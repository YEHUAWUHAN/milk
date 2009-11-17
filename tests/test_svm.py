import milk.supervised.svm
from milk.supervised.svm import svm_learn_smo, svm_learn_libsvm, _svm_apply, learn_sigmoid_constants, svm_sigmoidal_correction
import numpy
import random
import numpy as np
import milk.supervised.svm
eps=1e-3
def approximate(a,b):
    a=numpy.asanyarray(a)
    b=numpy.asanyarray(b)
    return numpy.abs(a-b).max() < eps

def assert_kkt(SVM):
    X,Y,Alphas,b,C,kernel=SVM
    N=len(Alphas)
    for i in xrange(N):
        if Alphas[i] == 0.:
            assert Y[i]*_svm_apply(SVM,X[i])+eps >= 1
        elif Alphas[i] == C:
            assert Y[i]*_svm_apply(SVM,X[i])-eps <= 1
        else:
            assert abs(Y[i]*_svm_apply(SVM,X[i])-1) <= eps

def assert_all_correctly_classified(SVM,X,Y):
    N = len(X)
    for i in xrange(N):
        assert _svm_apply(SVM,X[i]) * Y[i] > 0

def assert_more_than_50(SVM,X,Y):
    N = len(X)
    correct = 0
    for i in xrange(N):
        correct += (_svm_apply(SVM,X[i]) * Y[i] > 0)
    assert correct > N/2

def test_simplest():
    X=numpy.array([
        [1],
        [2],
        ])
    Y=numpy.array([1,-1])
    C=4.
    kernel=numpy.dot
    Alphas,b=svm_learn_smo(X,Y,kernel,C)
    SVM=(X,Y,Alphas,b,C,kernel)
    Alphas_,b_=svm_learn_libsvm(X,Y,kernel,C)
    assert approximate(Alphas,Alphas_)
    assert approximate(b,b_)
    assert approximate(Alphas,[2.,2.])
    assert approximate(b,-3)
    assert_kkt(SVM)
    assert_all_correctly_classified(SVM,X,Y)

def test_more_complex_smo():
    X=numpy.array([
        [1,0],
        [2,1],
        [2,0],
        [4,2],
        [0,1],
        [0,2],
        [1,2],
        [2,8]])
    Y=numpy.array([1,1,1,1,-1,-1,-1,-1])
    C=4.
    kernel=numpy.dot
    Alphas,b=svm_learn_smo(X,Y,kernel,C)

    def verify():
        SVM=(X,Y,Alphas,b,C,kernel)
        sv=numpy.array([1,1,0,0,1,0,1,0])
        nsv=~sv
        computed_sv = (Alphas > 0) & (Alphas < C)
        computed_nsv = ~computed_sv
        assert_kkt(SVM)
        assert numpy.all((sv-computed_sv) >= 0) # computed_sv in sv
        assert numpy.all((computed_nsv-nsv) >= 0) # nsv in computed_nsv
        assert_all_correctly_classified(SVM,X,Y)

    verify()
    Alphas,b=svm_learn_libsvm(X,Y,kernel,C)
    verify()

def rbf(xi,xj):
    return numpy.exp(-((xi-xj)**2).sum())

def test_rbf():
    X=numpy.array([
        [0,0,0],
        [1,1,1],
        ])
    Y=numpy.array([ 1, -1 ])
    C=10
    Alphas,b=svm_learn_smo(X,Y,rbf,C)
    SVM=(X,Y,Alphas,b,C,rbf)
    assert_all_correctly_classified(SVM,X,Y)

    Alphas,b=svm_learn_libsvm(X,Y,rbf,C)
    SVM=(X,Y,Alphas,b,C,rbf)
    assert_all_correctly_classified(SVM,X,Y)

def test_random():
    R=numpy.random.RandomState(123)
    X=R.rand(10,3)
    X[:5]+=1.
    C=2
    Y=numpy.ones(10)
    Y[5:] *= -1
    Alphas,b=svm_learn_smo(X,Y,rbf,C)
    SVM=(X,Y,Alphas,b,C,rbf)
    assert_more_than_50(SVM,X,Y)

    Alphas,b=svm_learn_libsvm(X,Y,rbf,C)
    SVM=(X,Y,Alphas,b,C,rbf)
    assert_more_than_50(SVM,X,Y)

def test_platt_correction():
    F=numpy.ones(10)
    L=numpy.ones(10)
    F[:5] *= -1
    L[:5] *= 0
    A,B=learn_sigmoid_constants(F,L)
    assert 1./(1.+numpy.exp(+10*A+B)) > .99
    assert 1./(1.+numpy.exp(-10*A+B)) <.01

def test_platt_correction_class():
    F=numpy.ones(10)
    L=numpy.ones(10)
    F[:5] *= -1
    L[:5] *= 0
    corrector = svm_sigmoidal_correction()
    A,B = learn_sigmoid_constants(F,L)
    model = corrector.train(F,L)
    assert model.A == A
    assert model.B == B
    assert model.apply(10) > .99
    assert model.apply(-10) < .01

def test_perfect():
    data = numpy.zeros((10,2))
    data[5:] = 1
    labels = numpy.zeros(10)
    labels[5:] = 1
    classifier=milk.supervised.svm.svm_raw(kernel=milk.supervised.svm.rbf_kernel(1),C=4)
    model = classifier.train(data,labels)
    assert numpy.all( (numpy.array([model.apply(data[i]) for i in xrange(10)]) > 0) == labels )

def test_smart_rbf():
    import milksets.wine
    features,labels = milksets.wine.load()
    labels = (labels == 1)
    kernel = milk.supervised.svm.rbf_kernel(2.**-4)
    C = milk.supervised.svm.svm_raw(C=2.,kernel=kernel)
    model = C.train(features,labels)
    smartkernel = [model.apply(f) for f in features]
    del kernel.kernel_nr_
    del kernel.kernel_arg_
    C = milk.supervised.svm.svm_raw(C=2.,kernel=kernel)
    model = C.train(features,labels)
    dumbkernel = [model.apply(f) for f in features]
    assert smartkernel == dumbkernel


def test_preprockernel():
    def test_preproc(kernel):
        X = np.random.rand(200,20)
        Qs = np.random.rand(100, 20)
        prekernel = kernel.preprocess(X)
        Qs = np.random.rand(10, 20)
        for q in Qs:
            preprocval = prekernel(q)
            procval = np.array([kernel(q,x) for x in X])
            assert np.allclose(preprocval, procval)
    yield test_preproc, milk.supervised.svm.rbf_kernel(2.)

