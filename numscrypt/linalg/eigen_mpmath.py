##################################################################################################
#
# This module is an adaptation for Numscrypt and Transcrypt of mpmath.matrix.eigen.py
#
# The whole of mpmath is distributed under the New or Revised BSD 3-clause License:
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#   a. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#   b. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#   c. Neither the name of mpmath nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
# The following copyrights are relevant:
#
# Copyright (C) 2005-2017 Fredrik Johansson and mpmath contributors
# (w.r.t. the mpmath library as a whole)
#
# Copyright (C) 2013 Timo Hartmann, mpmath contributor (thartmann15 at gmail.com)
# (w.r.t the original module for the eigenvalue problem)
#
# Copyright (C) 2017 Jacques de Hooge (jdeh@transcrypt.org)
# (w.r.t. the adaptation for Numscrypt and Transcrypt)
#
##################################################################################################

# __pragma__ ('opov')

# BEGIN compatibility stuff

from math import *
import cmath
from numscrypt import *

def isinf (x):  # !!! Todo
    return False
    
def hypot (x, y):
    return sqrt (x * x + y * y)
    
ctx_eps = 1e-15
ctx_dps = 15
    
ctx_one = 1
ctx_prec = 53

def ctx_ldexp (x, n):
    return x * 2**n

# END compatibility stuff
    
"""
The eigenvalue problem
----------------------

This file contains routines for the eigenvalue problem.

high level routines:

  hessenberg : reduction of a real or complex square matrix to upper Hessenberg form
  schur : reduction of a real or complex square matrix to upper Schur form
  eig : eigenvalues and eigenvectors of a real or complex square matrix

low level routines:

  hessenberg_reduce_0 : reduction of a real or complex square matrix to upper Hessenberg form
  hessenberg_reduce_1 : auxiliary routine to hessenberg_reduce_0
  qr_step : a single implicitly shifted QR step for an upper Hessenberg matrix
  hessenberg_qr : Schur decomposition of an upper Hessenberg matrix
  eig_tr_r : right eigenvectors of an upper triangular matrix
  eig_tr_l : left  eigenvectors of an upper triangular matrix
"""

def hessenberg_reduce_0(A, T):
    """
    This routine computes the (upper) Hessenberg decomposition of a square matrix A.
    Given A, an unitary matrix Q is calculated such that

               Q' A Q = H              and             Q' Q = Q Q' = 1

    where H is an upper Hessenberg matrix, meaning that it only contains zeros
    below the first subdiagonal. Here ' denotes the hermitian transpose (i.e.
    transposition and conjugation).

    parameters:
      A         (input/output) On input, A contains the square matrix A of
                dimension (n,n). On output, A contains a compressed representation
                of Q and H.
      T         (output) An array of length n containing the first elements of
                the Householder reflectors.
    """

    # internally we work with householder reflections from the right.
    # let u be a row vector (i.e. u[i]=A[i,:i]). then
    # Q is build up by reflectors of the type (1-v'v) where v is a suitable
    # modification of u. these reflectors are applyed to A from the right.
    # because we work with reflectors from the right we have to start with
    # the bottom row of A and work then upwards (this corresponds to
    # some kind of RQ decomposition).
    # the first part of the vectors v (i.e. A[i,:(i-1)]) are stored as row vectors
    # in the lower left part of A (excluding the diagonal and subdiagonal).
    # the last entry of v is stored in T.
    # the upper right part of A (including diagonal and subdiagonal) becomes H.
    
    n = A.shape[0]
    if n <= 2: return

    for i in range(n-1, 1, -1):
        
        # scale the vector

        scale = 0
        for k in range(i):
            scale += abs(A[i,k].real) + abs(A[i,k].imag)

        scale_inv = 0
        if scale != 0:
            scale_inv = 1 / scale
            
        if scale == 0 or isinf(scale_inv):
            # sadly there are floating point numbers not equal to zero whose reciprocal is infinity
            T[i] = 0
            A[i,i-1] = 0
            continue

        # calculate parameters for housholder transformation

        H = 0
        for k in range(i):
            A[i,k] *= scale_inv
            rr = A[i,k].real
            ii = A[i,k].imag
            H += rr * rr + ii * ii

        F = A[i,i-1]
        f = abs(F)
        G = cmath.sqrt(H)
        A[i,i-1] = - G * scale
        
        if f == 0:
            T[i] = G
        else:
            ff = F / f
            T[i] = F + G * ff
            A[i,i-1] *= ff

        H += G * f
        H = 1 / cmath.sqrt(H)
        
        T[i] *= H
        for k in range(i - 1):
            A[i,k] *= H
        
        for j in range(i):
            # apply housholder transformation (from right)

            G = T[i].conjugate() * A[j,i-1]

            
            for k in range(i-1):
                G += A[i,k].conjugate() * A[j,k]

                
            A[j,i-1] -= G * T[i]
            for k in range(i-1):
                A[j,k] -= G * A[i,k]

        
        for j in range(n):
            # apply housholder transformation (from left)

            G = T[i] * A[i-1,j]
            for k in range(i-1):
                G += A[i,k] * A[k,j]

            A[i-1,j] -= G * T[i].conjugate()
            for k in range(i-1):
                A[k,j] -= G * A[i,k].conjugate()

def hessenberg_reduce_1(A, T):
    """
    This routine forms the unitary matrix Q described in hessenberg_reduce_0.

    parameters:
      A    (input/output) On input, A is the same matrix as delivered by
           hessenberg_reduce_0. On output, A is set to Q.

      T    (input) On input, T is the same array as delivered by hessenberg_reduce_0.
    """

    n = A.shape[0]

    if n == 1:
        A[0,0] = 1
        return

    A[0,0] = A[1,1] = 1
    A[0,1] = A[1,0] = 0

    for i in range(2, n):
        if T[i] != complex (0):     # !!! Conversion shouldn't be needed

            for j in range(i):
                G = T[i] * A[i-1,j]
                for k in range(i-1):
                    G += A[i,k] * A[k,j]

                A[i-1,j] -= G * T[i].conjugate()
                for k in range(i-1):
                    A[k,j] -= G * A[i,k].conjugate()

        A[i,i] = 1
        for j in range(i):
            A[j,i] = A[i,j] = 0

            
def hessenberg(A, overwrite_a = False):
    """
    This routine computes the Hessenberg decomposition of a square matrix A.
    Given A, an unitary matrix Q is determined such that

          Q' A Q = H                and               Q' Q = Q Q' = 1

    where H is an upper right Hessenberg matrix. Here ' denotes the hermitian
    transpose (i.e. transposition and conjugation).

    input:
      A            : a real or complex square matrix
      overwrite_a  : if true, allows modification of A which may improve
                     performance. if false, A is not modified.

    output:
      Q : an unitary matrix
      H : an upper right Hessenberg matrix

    example:
      >>> from mpmath import mp
      >>> A = mp.matrix([[3, -1, 2], [2, 5, -5], [-2, -3, 7]])
      >>> Q, H = mp.hessenberg(A)
      >>> mp.nprint(H, 3) # doctest:+SKIP
      [  3.15  2.23  4.44]
      [-0.769  4.85  3.05]
      [   0.0  3.61   7.0]
      >>> print(mp.chop(A - Q * H * Q.transpose_conj()))
      [0.0  0.0  0.0]
      [0.0  0.0  0.0]
      [0.0  0.0  0.0]

    return value:   (Q, H)
    """

    n = A.shape[0]

    if n == 1:
        return (array([[1]], A.dtype), A)

    if not overwrite_a:
        A = copy (A)

    T = empty((n,), A.dtype) # !!! n, 1 -> n

    hessenberg_reduce_0(A, T)
    Q = copy (A.copy)
    hessenberg_reduce_1(Q, T)

    for x in range(n):
        for y in range(x+2, n):
            A[y,x] = 0

    return Q, A


###########################################################################


def qr_step(n0, n1, A, Q, shift):
    """
    This subroutine executes a single implicitly shifted QR step applied to an
    upper Hessenberg matrix A. Given A and shift as input, first an QR
    decomposition is calculated:

      Q R = A - shift * 1 .

    The output is then following matrix:

      R Q + shift * 1

    parameters:
      n0, n1    (input) Two integers which specify the submatrix A[n0:n1,n0:n1]
                on which this subroutine operators. The subdiagonal elements
                to the left and below this submatrix must be deflated (i.e. zero).
                following restriction is imposed: n1>=n0+2
      A         (input/output) On input, A is an upper Hessenberg matrix.
                On output, A is replaced by "R Q + shift * 1"
      Q         (input/output) The parameter Q is multiplied by the unitary matrix
                Q arising from the QR decomposition. Q can also be false, in which
                case the unitary matrix Q is not computed.
      shift     (input) a complex number specifying the shift. idealy close to an
                eigenvalue of the bottemmost part of the submatrix A[n0:n1,n0:n1].

    references:
      Stoer, Bulirsch - Introduction to Numerical Analysis.
      Kresser : Numerical Methods for General and Structured Eigenvalue Problems
    """

    # implicitly shifted and bulge chasing is explained at p.398/399 in "Stoer, Bulirsch - Introduction to Numerical Analysis"
    # for bulge chasing see also "Watkins - The Matrix Eigenvalue Problem" sec.4.5,p.173

    # the Givens rotation we used is determined as follows: let c,s be two complex
    # numbers. then we have following relation:
    #
    #     v = sqrt(|c|^2 + |s|^2)
    #
    #     1/v [ c~  s~]  [c] = [v]
    #         [-s   c ]  [s]   [0]
    #
    # the matrix on the left is our Givens rotation.
    
    n = A.shape[0]

    # first step

    # calculate givens rotation
    c = A[n0  ,n0] - shift
    s = A[n0+1,n0]

    v = hypot(hypot(c.real, c.imag), hypot(s.real, s.imag))

    if v == 0:
        v = 1
        c = 1
        s = 0
    else:
        c /= v
        s /= v

    for k in range(n0, n):
        # apply givens rotation from the left
        x = A[n0  ,k]
        y = A[n0+1,k]

        A[n0  ,k] = c.conjugate() * x + s.conjugate() * y
        A[n0+1,k] =           -s  * x +            c  * y
    
    for k in range(min(n1, n0+3)):
        # apply givens rotation from the right
        x = A[k,n0  ]
        y = A[k,n0+1]
        A[k,n0  ] =             c  * x +            s  * y
        A[k,n0+1] = -s.conjugate() * x + c.conjugate() * y

    if not isinstance(Q, bool):
        for k in range(n):
            # eigenvectors
            x = Q[k,n0  ]
            y = Q[k,n0+1]
            Q[k,n0  ] =             c  * x +            s  * y
            Q[k,n0+1] = -s.conjugate() * x + c.conjugate() * y

    # chase the bulge
    
    for j in range(n0, n1 - 2):
        # calculate givens rotation

        c = A[j+1,j]
        s = A[j+2,j]

        v = hypot(hypot(c.real, c.imag), hypot(s.real, s.imag))

        if v == 0:
            A[j+1,j] = 0
            v = 1
            c = 1
            s = 0
        else:
            A[j+1,j] = v
            c /= v
            s /= v

        A[j+2,j] = 0
    
        for k in range(j+1, n):
            # apply givens rotation from the left
            x = A[j+1,k]
            y = A[j+2,k]
            A[j+1,k] = c.conjugate() * x + s.conjugate() * y
            A[j+2,k] =           -s  * x +            c  * y
    
        for k in range(min(n1, j+4)):
            # apply givens rotation from the right
            x = A[k,j+1]
            y = A[k,j+2]
            A[k,j+1] =             c  * x +            s  * y
            A[k,j+2] = -s.conjugate() * x + c.conjugate() * y
    
        if not isinstance(Q, bool):
            for k in range(n):
                # eigenvectors
                x = Q[k,j+1]
                y = Q[k,j+2]
                Q[k,j+1] =             c  * x +            s  * y
                Q[k,j+2] = -s.conjugate() * x + c.conjugate() * y



def hessenberg_qr(A, Q):
    """
    This routine computes the Schur decomposition of an upper Hessenberg matrix A.
    Given A, an unitary matrix Q is determined such that

          Q' A Q = R                   and                  Q' Q = Q Q' = 1

    where R is an upper right triangular matrix. Here ' denotes the hermitian
    transpose (i.e. transposition and conjugation).

    parameters:
      A         (input/output) On input, A contains an upper Hessenberg matrix.
                On output, A is replace by the upper right triangluar matrix R.

      Q         (input/output) The parameter Q is multiplied by the unitary
                matrix Q arising from the Schur decomposition. Q can also be
                false, in which case the unitary matrix Q is not computated.
    """

    n = A.shape[0]

    norm = 0
    for x in range(n):
        for y in range(min(x+2, n)):
            norm += A[y,x].real * A[y,x].real + A[y,x].imag * A[y,x].imag
    norm = sqrt(norm) / n
    
    if norm == 0:
        return

    n0 = 0
    n1 = n

    eps = ctx_eps / (100 * n)
    
    maxits = ctx_dps * 4

    its = totalits = 0                           

    while True:
        # kressner p.32 algo 3
        # the active submatrix is A[n0:n1,n0:n1]

        k = n0
        
        while k + 1 < n1:
            s = abs(A[k,k].real) + abs(A[k,k].imag) + abs(A[k+1,k+1].real) + abs (A[k+1,k+1].imag)

            if s < eps * norm:
                s = norm              
                
            if abs(A[k+1,k]) < eps * s:
                break
            k += 1
     
        if k + 1 < n1:
            # deflation found at position (k+1, k)

            A[k+1,k] = 0  # !!! Make this unneeded, the complex, that is
            n0 = k + 1

            its = 0

            if n0 + 1 >= n1:
                # block of size at most two has converged
                n0 = 0
                n1 = k + 1
                if n1 < 2:
                    # QR algorithm has converged
                    return
        else:
            if (its % 30) == 10:
                # exceptional shift
                shift = A[n1-1,n1-2]
            elif (its % 30) == 20:
                # exceptional shift
                shift = abs(A[n1-1,n1-2])
            elif (its % 30) == 29:
                # exceptional shift
                shift = norm
            else:
                
                #    A = [ a b ]       det(x-A)=x*x-x*tr(A)+det(A)
                #        [ c d ]
                #
                # eigenvalues bad:   (tr(A)+sqrt((tr(A))**2-4*det(A)))/2
                #     bad because of cancellation if |c| is small and |a-d| is small, too.
                #
                # eigenvalues good:     (a+d+sqrt((a-d)**2+4*b*c))/2

                t =  A[n1-2,n1-2] + A[n1-1,n1-1]
                s = (A[n1-1,n1-1] - A[n1-2,n1-2]) ** 2 + 4 * A[n1-1,n1-2] * A[n1-2,n1-1]
                if s.real > 0:
                    s = cmath.sqrt(s)
                else:
                    s = cmath.sqrt(-s) * 1j
                a = (t + s) / 2
                b = (t - s) / 2
                if abs(A[n1-1,n1-1] - a) > abs(A[n1-1,n1-1] - b):
                    shift = b
                else:
                    shift = a

            its += 1
            totalits += 1

            qr_step(n0, n1, A, Q, shift)
            
            if its > maxits:
                raise RuntimeError("qr: failed to converge after %d steps" % its)

def schur(A, overwrite_a = False):
    """
    This routine computes the Schur decomposition of a square matrix A.
    Given A, an unitary matrix Q is determined such that

          Q' A Q = R                and               Q' Q = Q Q' = 1

    where R is an upper right triangular matrix. Here ' denotes the
    hermitian transpose (i.e. transposition and conjugation).

    input:
      A            : a real or complex square matrix
      overwrite_a  : if true, allows modification of A which may improve
                     performance. if false, A is not modified.

    output:
      Q : an unitary matrix
      R : an upper right triangular matrix

    return value:   (Q, R)

    example:
      >>> from mpmath import mp
      >>> A = mp.matrix([[3, -1, 2], [2, 5, -5], [-2, -3, 7]])
      >>> Q, R = mp.schur(A)
      >>> mp.nprint(R, 3) # doctest:+SKIP
      [2.0  0.417  -2.53]
      [0.0    4.0  -4.74]
      [0.0    0.0    9.0]
      >>> print(mp.chop(A - Q * R * Q.transpose_conj()))
      [0.0  0.0  0.0]
      [0.0  0.0  0.0]
      [0.0  0.0  0.0]

    warning: The Schur decomposition is not unique.
    """

    n = A.shape[0]

    if n == 1:
        return (array([[1]], A.dtype), A)

    if not overwrite_a:
        A = copy (A)

    T = empty((n,), A.dtype) # !!! n, 1 -> n

    hessenberg_reduce_0(A, T)
    Q = copy (A)
    hessenberg_reduce_1(Q, T)

    for x in range(n):
        for y in range(x + 2, n):
            A[y,x] = 0

    hessenberg_qr(A, Q)

    return Q, A


def eig_tr_r(A):
    """
    This routine calculates the right eigenvectors of an upper right triangular matrix.

    input:
      A      an upper right triangular matrix

    output:
      ER     a matrix whose columns form the right eigenvectors of A

    return value: ER
    """

    # this subroutine is inspired by the lapack routines ctrevc.f,clatrs.f

    n = A.shape[0] 
    
    ER = identity(n, A.dtype)

    eps = ctx_eps

    unfl = ctx_ldexp(ctx_one, -ctx_prec * 30)
    # since mpmath effectively has no limits on the exponent, we simply scale doubles up
    # original double has prec*20

    smlnum = unfl * (n / eps)
    simin = 1 / sqrt(eps)

    rmax = 1

    for i in range(1, n):
        s = A[i,i]

        smin = max(eps * abs(s), smlnum)

        for j in range(i - 1, -1, -1):

            r = 0
            for k in range(j + 1, i + 1):
                r += A[j,k] * ER[k,i]

            t = A[j,j] - s
            if abs(t) < smin:
                t = smin

            r = -r / t
            
            ER[j,i] = r

            rmax = max(rmax, abs(r))
            if rmax > simin:
                for k in range(j, i+1):
                    ER[k,i] /= rmax
                rmax = 1

        if rmax != 1:
            for k in range(i + 1):
                ER[k,i] /= rmax

    return ER

def eig_tr_l(A):
    """
    This routine calculates the left eigenvectors of an upper right triangular matrix.

    input:
      A      an upper right triangular matrix

    output:
      EL     a matrix whose rows form the left eigenvectors of A

    return value:  EL
    """

    n = A.shape[0]

    EL = identity(n, A.dtype)

    eps = ctx_eps

    unfl = ctx_ldexp(ctx_one, -ctx_prec * 30)
    # since mpmath effectively has no limits on the exponent, we simply scale doubles up
    # original double has prec*20

    smlnum = unfl * (n / eps)
    simin = 1 / cmath.sqrt(eps)

    rmax = 1

    for i in range(n - 1):
        s = A[i,i]

        smin = max(eps * abs(s), smlnum)

        for j in range(i + 1, n):

            r = 0
            for k in range(i, j):
                r += EL[i,k] * A[k,j]

            t = A[j,j] - s
            if abs(t) < smin:
                t = smin

            r = -r / t
            EL[i,j] = r

            rmax = max(rmax, abs(r))
            if rmax > simin:
                for k in range(i, j + 1):
                    EL[i,k] /= rmax
                rmax = 1

        if rmax != 1:
            for k in range(i, n):
                EL[i,k] /= rmax

    return EL

def eig(A, left = False, right = True, overwrite_a = False):
    """
    This routine computes the eigenvalues and optionally the left and right
    eigenvectors of a square matrix A. Given A, a vector E and matrices ER
    and EL are calculated such that

                        A ER[:,i] =         E[i] ER[:,i]
                EL[i,:] A         = EL[i,:] E[i]

    E contains the eigenvalues of A. The columns of ER contain the right eigenvectors
    of A whereas the rows of EL contain the left eigenvectors.


    input:
      A           : a real or complex square matrix of shape (n, n)
      left        : if true, the left eigenvectors are calulated.
      right       : if true, the right eigenvectors are calculated.
      overwrite_a : if true, allows modification of A which may improve
                    performance. if false, A is not modified.

    output:
      E    : a list of length n containing the eigenvalues of A.
      ER   : a matrix whose columns contain the right eigenvectors of A.
      EL   : a matrix whose rows contain the left eigenvectors of A.

    return values:
       E            if left and right are both false.
      (E, ER)       if right is true and left is false.
      (E, EL)       if left is true and right is false.
      (E, EL, ER)   if left and right are true.


    examples:
      >>> from mpmath import mp
      >>> A = mp.matrix([[3, -1, 2], [2, 5, -5], [-2, -3, 7]])
      >>> E, ER = mp.eig(A)
      >>> print(mp.chop(A * ER[:,0] - E[0] * ER[:,0]))
      [0.0]
      [0.0]
      [0.0]

      >>> E, EL, ER = mp.eig(A,left = True, right = True)
      >>> E, EL, ER = mp.eig_sort(E, EL, ER)
      >>> mp.nprint(E)
      [2.0, 4.0, 9.0]
      >>> print(mp.chop(A * ER[:,0] - E[0] * ER[:,0]))
      [0.0]
      [0.0]
      [0.0]
      >>> print(mp.chop( EL[0,:] * A - EL[0,:] * E[0]))
      [0.0  0.0  0.0]

    warning:
     - If there are multiple eigenvalues, the eigenvectors do not necessarily
       span the whole vectorspace, i.e. ER and EL may have not full rank.
       Furthermore in that case the eigenvectors are numerical ill-conditioned.
     - In the general case the eigenvalues have no natural order.

    see also:
      - eigh (or eigsy, eighe) for the symmetric eigenvalue problem.
      - eig_sort for sorting of eigenvalues and eigenvectors
    """

    n = A.shape[0]

    if n == 1:
        if left and (not right):
            return ([A[0]], array([[1]], A.dtype))

        if right and (not left):
            return ([A[0]], array([[1]], A.dtype))

        return ([A[0]], array([[1]], A.dtype), array([[1]], A.dtype))

    if not overwrite_a:
        A = copy (A)

    T = zeros((n,), 'complex64')

    hessenberg_reduce_0(A, T)

    if left or right:
        Q = copy (A)
        hessenberg_reduce_1(Q, T) 
    else:
        Q = False
        
            
    for x in range(n):
        for y in range(x + 2, n):
            A[y,x] = 0

    hessenberg_qr(A, Q)
    
    E = [complex (0) for i in range(n)]
    for i in range(n):
        E[i] = A[i,i]

    if not (left or right):
        return E

    if left:
        EL = eig_tr_l(A)
        EL = EL @ Q.conjugate().transpose()

    if right:
        ER = eig_tr_r(A)
        ER = Q @ ER

    if left and (not right):
        return (E, EL)

    if right and (not left):
        return (E, ER)

    return (E, EL, ER)

'''
def eig_sort(ctx, E, EL = False, ER = False, f = "real"):
    """
    This routine sorts the eigenvalues and eigenvectors delivered by ``eig``.

    parameters:
      E  : the eigenvalues as delivered by eig
      EL : the left  eigenvectors as delivered by eig, or false
      ER : the right eigenvectors as delivered by eig, or false
      f  : either a string ("real" sort by increasing real part, "imag" sort by
           increasing imag part, "abs" sort by absolute value) or a function
           mapping complexes to the reals, i.e. ``f = lambda x: -mp.re(x) ``
           would sort the eigenvalues by decreasing real part.

    return values:
       E            if EL and ER are both false.
      (E, ER)       if ER is not false and left is false.
      (E, EL)       if EL is not false and right is false.
      (E, EL, ER)   if EL and ER are not false.

    example:
      >>> from mpmath import mp
      >>> A = mp.matrix([[3, -1, 2], [2, 5, -5], [-2, -3, 7]])
      >>> E, EL, ER = mp.eig(A,left = True, right = True)
      >>> E, EL, ER = mp.eig_sort(E, EL, ER)
      >>> mp.nprint(E)
      [2.0, 4.0, 9.0]
      >>> E, EL, ER = mp.eig_sort(E, EL, ER,f = lambda x: -mp.re(x))
      >>> mp.nprint(E)
      [9.0, 4.0, 2.0]
      >>> print(mp.chop(A * ER[:,0] - E[0] * ER[:,0]))
      [0.0]
      [0.0]
      [0.0]
      >>> print(mp.chop( EL[0,:] * A - EL[0,:] * E[0]))
      [0.0  0.0  0.0]
    """

    if isinstance(f, str):  #!!! No idea...
        if f == "real":
            f = ctx.re
        elif f == "imag":
            f = ctx.im
        elif cmp == "abs":
            f = abs
        else:
            raise RuntimeError("unknown function %s" % f)

    n = len(E)

    # Sort eigenvalues (bubble-sort)

    for i in range(n):
        imax = i
        s = f(E[i])         # s is the current maximal element

        for j in range(i + 1, n):
            c = f(E[j])
            if c < s:
                s = c
                imax = j

        if imax != i:
            # swap eigenvalues

            z = E[i]
            E[i] = E[imax]
            E[imax] = z

            if not isinstance(EL, bool):
                for j in range(n):
                    z = EL[i,j]
                    EL[i,j] = EL[imax,j]
                    EL[imax,j] = z

            if not isinstance(ER, bool):
                for j in range(n):
                    z = ER[j,i]
                    ER[j,i] = ER[j,imax]
                    ER[j,imax] = z

    if isinstance(EL, bool) and isinstance(ER, bool):
        return E

    if isinstance(EL, bool) and not(isinstance(ER, bool)):
        return (E, ER)

    if isinstance(ER, bool) and not(isinstance(EL, bool)):
        return (E, EL)

    return (E, EL, ER)
'''

