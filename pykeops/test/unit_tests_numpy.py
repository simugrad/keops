import os.path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + (os.path.sep + '..')*2)

import unittest
import itertools
import numpy as np

from pykeops.numpy.utils import np_kernel, grad_np_kernel, differences, squared_distances, log_sum_exp, np_kernel_sphere

from pykeops import gpu_available


class NumpyUnitTestCase(unittest.TestCase):

    M = int(10)
    N = int(6)
    D = int(3)
    E = int(3)

    x = np.random.rand(M, D)
    a = np.random.rand(M, E)
    f = np.random.rand(M, 1)
    y = np.random.rand(N, D)
    b = np.random.rand(N, E)
    g = np.random.rand(N, 1)
    sigma = np.array([0.4])

    type_to_test = ['float32', 'float64']

    @unittest.skipIf(not gpu_available, 'No GPU detected. Skip tests.')
    ############################################################
    def test_fshape_scp_specific(self):
    ############################################################
        from pykeops.numpy.shape_distance import FshapeScp
        for k, t in itertools.product(['gaussian', 'cauchy'], self.type_to_test):
            # Call cuda kernel
            kgeom = k
            ksig = 'gaussian'
            ksphere = 'gaussian_oriented'

            sigma_geom = 1.0
            sigma_sig = 1.0
            sigma_sphere = np.pi / 2

            # Call cuda kernel
            my_fshape_scp = FshapeScp(kernel_geom=kgeom, kernel_sig=ksig, kernel_sphere=ksphere, cuda_type=t)
            gamma = my_fshape_scp(self.x.astype(t), self.y.astype(t),
                                  self.f.astype(t), self.g.astype(t),
                                  self.a.astype(t), self.b.astype(t),
                                  sigma_geom=sigma_geom, sigma_sig=sigma_sig, sigma_sphere=sigma_sphere).ravel()

            # Python version
            areaa = np.linalg.norm(self.a, axis=1)
            areab = np.linalg.norm(self.b, axis=1)

            nalpha = self.a / areaa[:, np.newaxis]
            nbeta = self.b / areab[:, np.newaxis]

            gamma_py = np.sum((areaa[:, np.newaxis] * areab[np.newaxis, :])
                              * np_kernel(self.x, self.y, sigma_geom, kgeom)
                              * np_kernel(self.f, self.g, sigma_sig, ksig)
                              * np_kernel_sphere(nalpha, nbeta, sigma_sphere, ksphere), axis=1)

            # compare output
            self.assertTrue(np.allclose(gamma, gamma_py, atol=1e-6))

    @unittest.skipIf(not gpu_available,'No GPU detected. Skip tests.')
    ############################################################
    def test_gaussian_conv_specific(self):
    ############################################################
        from pykeops.numpy.convolutions.radial_kernel import RadialKernelConv
        for k, t in itertools.product(['gaussian', 'laplacian', 'cauchy', 'inverse_multiquadric'], self.type_to_test):
            with self.subTest(k=k):
                # Call cuda kernel
                my_radial_conv = RadialKernelConv(t)
                gamma = my_radial_conv(self.x.astype(t), self.y.astype(t), self.b.astype(t), self.sigma.astype(t), kernel = k)

                # Numpy version
                gamma_py = np.matmul(np_kernel(self.x, self.y, self.sigma, kernel=k), self.b)

                # compare output
                self.assertTrue(np.allclose(gamma, gamma_py, atol=1e-6))

    @unittest.skipIf(not gpu_available, 'No GPU detected. Skip tests.')
    ############################################################
    def test_gaussian_grad1conv_specific(self):
    ############################################################
        from pykeops.numpy.convolutions.radial_kernel import RadialKernelGrad1conv
        for k, t in itertools.product(['gaussian', 'laplacian', 'cauchy', 'inverse_multiquadric'], self.type_to_test):
            with self.subTest(k=k, t=t):
                # Call cuda kernel
                my_radial_conv = RadialKernelGrad1conv(t)
                gamma = my_radial_conv(self.a.astype(t), self.x.astype(t), self.y.astype(t), self.b.astype(t), self.sigma.astype(t), kernel=k)

                # Numpy version
                tmp = differences(self.x, self.y) * grad_np_kernel(self.x, self.y, self.sigma, kernel=k)
                gamma_py = 2 * (np.sum(self.a * (np.matmul(tmp, self.b)), axis=2)).T

                # compare output
                self.assertTrue( np.allclose(gamma, gamma_py,atol=1e-6))

    ############################################################
    def test_generic_syntax_sum(self):
    ############################################################
        from pykeops.numpy.generic.generic_red import Genred
        aliases = ['p=Pm(0,1)', 'a=Vy(1,1)', 'x=Vx(2,3)', 'y=Vy(3,3)']
        formula = 'Square(p-a)*Exp(x+y)'
        axis = 1  # 0 means summation over i, 1 means over j

        if gpu_available:
            backend_to_test = ['auto', 'GPU_1D', 'GPU_2D', 'GPU']
        else:
            backend_to_test = ['auto']

        for b, t in itertools.product(backend_to_test, self.type_to_test):
            with self.subTest(b=b, t=t):

                # Call cuda kernel
                myconv = Genred(formula, aliases, reduction_op='Sum', axis=axis, cuda_type=t)
                gamma_keops = myconv(self.sigma.astype(t), self.g.astype(t), self.x.astype(t), self.y.astype(t), backend=b)

                # Numpy version
                gamma_py = np.sum((self.sigma - self.g)**2
                                  * np.exp((self.y.T[:,:,np.newaxis] + self.x.T[:,np.newaxis,:])), axis=1).T

                # compare output
                self.assertTrue( np.allclose(gamma_keops, gamma_py , atol=1e-6))

    ############################################################
    def test_generic_syntax_lse(self):
    ############################################################
        from pykeops.numpy.generic.generic_red import Genred
        aliases = ['p=Pm(0,1)', 'a=Vy(1,1)', 'x=Vx(2,3)', 'y=Vy(3,3)']
        formula = 'Square(p-a)*Exp(-SqNorm2(x-y))'

        if gpu_available:
            backend_to_test = ['auto', 'GPU_1D', 'GPU_2D', 'GPU']
        else:
            backend_to_test = ['auto']

        for b, t in itertools.product(backend_to_test, self.type_to_test):
            with self.subTest(b=b, t=t):

                # Call cuda kernel
                myconv = Genred(formula, aliases, reduction_op='LogSumExp', axis=1, cuda_type=t)
                gamma_keops= myconv(self.sigma.astype(t), self.g.astype(t), self.x.astype(t), self.y.astype(t), backend=b)

                # Numpy version
                gamma_py = log_sum_exp((self.sigma - self.g.T)**2 * np.exp(-squared_distances(self.x, self.y)), axis=1)
                
                # compare output
                self.assertTrue(np.allclose(gamma_keops.ravel(), gamma_py, atol=1e-6))
            
    ############################################################
    def test_non_contiguity(self):
    ############################################################
        from pykeops.numpy.generic.generic_red import Genred
        
        t = self.type_to_test[0]

        aliases = ['p=Pm(0,1)', 'a=Vy(1,1)', 'x=Vx(2,3)', 'y=Vy(3,3)']
        formula = 'Square(p-a)*Exp(-SqNorm2(y-x))'

        my_routine = Genred(formula, aliases, reduction_op='Sum', axis=1)
        gamma_keops1 = my_routine(self.sigma.astype(t), self.g.astype(t), self.x.astype(t), self.y.astype(t), backend='auto')
        
        yc_tmp = np.ascontiguousarray(self.y.T).T  # create a non contiguous copy
        gamma_keops2 = my_routine(self.sigma.astype(t), self.g.astype(t), self.x.astype(t), yc_tmp.astype(t))

        # check output
        self.assertFalse(yc_tmp.flags.c_contiguous)
        self.assertTrue(np.allclose(gamma_keops1, gamma_keops2))
        

if __name__ == '__main__':
    unittest.main()
