from numpy import array, zeros, dot, conjugate
from scipy.sparse import csr_matrix, isspmatrix
from scipy.sparse.sputils import upcast
from scipy.sparse.linalg.isolve.utils import make_system
from scipy.sparse.linalg.interface import aslinearoperator
from scipy import ceil, asmatrix
from warnings import warn
from pyamg.util.linalg import norm

__docformat__ = "restructuredtext en"

__all__ = ['cgnr']

def cgnr(A, b, x0=None, tol=1e-5, maxiter=None, xtype=None, M=None, callback=None, residuals=None):
    '''
    Conjugate Gradient, Normal Residual algorithm
    Applies CG to the normal equations, A.H A x = b
    Left preconditioning is supported
    Note that if A is not well-conditioned, this algorithm is unadvisable

    Parameters
    ----------
    A : {array, matrix, sparse matrix, LinearOperator}
        n x n, linear system to solve
    b : {array, matrix}
        right hand side, shape is (n,) or (n,1)
    x0 : {array, matrix}
        initial guess, default is a vector of zeros
    tol : float
        relative convergence tolerance, i.e. tol is scaled by ||b||
    maxiter : int
        maximum number of allowed iterations
    xtype : type
        dtype for the solution, default is automatic type detection
    M : {array, matrix, sparse matrix, LinearOperator}
        n x n, inverted preconditioner, i.e. solve M A.H A x = b.
    callback : function
        User-supplied funtion is called after each iteration as
        callback(xk), where xk is the current solution vector
    residuals : list
        residuals has the residual norm history,
        including the initial residual, appended to it
     
    Returns
    -------    
    (xNew, info)
    xNew -- an updated guess to the solution of Ax = b
    info -- halting status of cgnr
            0  : successful exit
            >0 : convergence to tolerance not achieved,
                 return iteration count instead.  
            <0 : numerical breakdown, or illegal input


    Notes
    -----
    The LinearOperator class is in scipy.sparse.linalg.interface.
    Use this class if you prefer to define A or M as a mat-vec routine
    as opposed to explicitly constructing the matrix.  A.psolve(..) is
    still supported as a legacy.
    
    Examples
    --------
    >>>from pyamg.krylov import *
    >>>from scipy import rand
    >>>import pyamg
    >>>A = pyamg.poisson((50,50))
    >>>b = rand(A.shape[0],)
    >>>(x,flag) = cgnr(A,b,maxiter=1500, tol=1e-8)
    >>>print pyamg.util.linalg.norm(b - A*x)

    References
    ----------
    Yousef Saad, "Iterative Methods for Sparse Linear Systems, 
    Second Edition", SIAM, pp. 276-7, 2003

    '''

    # Store the conjugate transpose explicitly as it will be used much later on
    if isspmatrix(A):
        AH = A.tocsr().conjugate().transpose()
    else:
        AH = aslinearoperator(asmatrix(A).H)
    
    # Convert inputs to linear system, with error checking  
    A,M,x,b,postprocess = make_system(A,M,x0,b,xtype)
    dimen = A.shape[0]
    
    # Choose type
    xtype = upcast(A.dtype, x.dtype, b.dtype, M.dtype)

    # Should norm(r) be kept
    if residuals == []:
        keep_r = True
    else:
        keep_r = False

    # Check iteration numbers
    # CGNE suffers from loss of orthogonality quite easily, so we arbitarily let the method go up to 130% over the
    # theoretically necessary limit of maxiter=dimen
    if maxiter == None:
        maxiter = int(ceil(1.3*dimen)) + 2
    elif maxiter < 1:
        raise ValueError('Number of iterations must be positive')
    elif maxiter > (1.3*dimen):
        warn('maximimum allowed inner iterations (maxiter) are the 130% times the number of degress of freedom')
        maxiter = int(ceil(1.3*dimen)) + 2

    # Scale tol by normb
    normb = norm(b) 
    if normb == 0:
        pass
    #    if callback != None:
    #        callback(0.0)
    #
    #    return (postprocess(zeros((dimen,), dtype=xtype)),0)
    else:
        tol = tol*normb

    # Prep for method
    r = b - A*x
    rhat = AH*r
    normr = norm(r)
    if keep_r:
        residuals.append(normr)

    # Is initial guess sufficient?
    if normr <= tol:
        if callback != None:    
            callback(x)
        
        return (postprocess(x), 0)
   
    # Begin CGNR

    # Apply preconditioner and calculate initial search direction
    z = M*rhat
    p = z.copy()
    old_zr = dot(conjugate(z), rhat)

    for iter in range(maxiter):

        # w_j = A p_j
        w = A*p

        # alpha = (z_j, rhat_j) / (w_j, w_j)
        alpha = old_zr/dot(conjugate(w), w)
        
        # x_{j+1} = x_j + alpha*p_j
        x += alpha*p

        # r_{j+1} = r_j - alpha*w_j
        r -= alpha*w

        # rhat_{j+1} = A.H*r_{j+1}
        rhat = AH*r

        # z_{j+1} = M*r_{j+1}
        z = M*rhat

        # beta = (z_{j+1}, rhat_{j+1}) / (z_j, rhat_j)
        new_zr = dot(conjugate(z), rhat)
        beta = new_zr / old_zr
        old_zr = new_zr

        # p_{j+1} = A.H*z_{j+1} + beta*p_j
        p *= beta
        p += z

        # Allow user access to residual
        if callback != None:
            callback( x )
        
        # test for convergence
        normr = norm(r)
        if keep_r:
            residuals.append(normr)
        if normr < tol:
            return (postprocess(x), 0)

    # end loop

    return (postprocess(x), iter+1)



#if __name__ == '__main__':
#    # from numpy import diag
#    # A = random((4,4))
#    # A = A*A.transpose() + diag([10,10,10,10])
#    # b = random((4,1))
#    # x0 = random((4,1))
#
#    from pyamg.gallery import stencil_grid
#    from numpy.random import random
#    A = stencil_grid([[0,-1,0],[-1,4,-1],[0,-1,0]],(150,150),dtype=float,format='csr')
#    b = random((A.shape[0],))
#    x0 = random((A.shape[0],))
#
#    import time
#    from scipy.sparse.linalg.isolve import cg as icg
#
#    print '\n\nTesting CGNR with %d x %d 2D Laplace Matrix'%(A.shape[0],A.shape[0])
#    t1=time.time()
#    (x,flag) = cgnr(A,b,x0,tol=1e-8,maxiter=100)
#    t2=time.time()
#    print '%s took %0.3f ms' % ('cgnr', (t2-t1)*1000.0)
#    print 'norm = %g'%(norm(b - A*x))
#    print 'info flag = %d'%(flag)
#
#    t1=time.time()
#    (y,flag) = icg(A,b,x0,tol=1e-8,maxiter=100)
#    t2=time.time()
#    print '\n%s took %0.3f ms' % ('linalg cg', (t2-t1)*1000.0)
#    print 'norm = %g'%(norm(b - A*y))
#    print 'info flag = %d'%(flag)
#