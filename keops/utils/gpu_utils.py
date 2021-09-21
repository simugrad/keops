import ctypes
from ctypes.util import find_library
from keops.utils.misc_utils import KeOps_Error, KeOps_Warning, find_library_abspath
from keops.config.config import cxx_compiler, build_path
import os

# Some constants taken from cuda.h
CUDA_SUCCESS = 0
CU_DEVICE_ATTRIBUTE_MAX_THREADS_PER_BLOCK = 1
CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK = 8

libcuda_folder = os.path.dirname(find_library_abspath("cuda"))
libnvrtc_folder = os.path.dirname(find_library_abspath("nvrtc"))


def get_cuda_include_path():
    # trying to auto detect location of cuda headers
    cuda_include_path = None
    for libpath in libcuda_folder, libnvrtc_folder:
        for libtag in "lib", "lib64":
            libtag = os.path.sep + libtag + os.path.sep
            if libtag in libpath:
                includetag = os.path.sep + "include" + os.path.sep
                includepath = libpath.replace(libtag,includetag) + os.path.sep
                if os.path.isfile(includepath + "cuda.h") and os.path.isfile(includepath + "nvrtc.h"):
                    return includepath
                    
    # if not successfull, we try a few standard locations:
    cuda_version = get_cuda_version()
    s = os.path.sep
    cuda_paths_to_try_start = [f"{s}opt{s}cuda{s}",
                        f"{s}usr{s}local{s}cuda{s}",
                        f"{s}usr{s}local{s}cuda-{cuda_version}{s}",
                        "/vol/cuda/10.2.89-cudnn7.6.4.38/",
                        ]
    cuda_paths_to_try_end = [f"include{s}",
                        f"targets{s}x86_64-linux{s}include{s}",
                        ]
    for path_start in cuda_paths_to_try_start:
        for path_end in cuda_paths_to_try_end:
            path = path_start + path_end
            if os.path.isfile(path + "cuda.h") and os.path.isfile(path + "nvrtc.h"):
                return path


def get_include_file_abspath(filename):
    import os
    tmp_file = build_path + "tmp.txt"
    os.system(f'echo "#include <{filename}>" | {cxx_compiler} -M -E -x c++ - | head -n 2 > {tmp_file}')
    strings = open(tmp_file).read().split()
    abspath = None
    for s in strings:
        if filename in s:
            abspath = s
    os.remove(tmp_file)
    return abspath

def cuda_include_fp16_path():
    """
    We look for float 16 cuda headers cuda_fp16.h and cuda_fp16.hpp
    based on cuda_path locations and return their directory
    """
    from keops.config.config import cuda_include_path
    if cuda_include_path:
        return cuda_include_path
    import os
    cuda_fp16_h_abspath = get_include_file_abspath("cuda_fp16.h")
    cuda_fp16_hpp_abspath = get_include_file_abspath("cuda_fp16.hpp")
    
    if cuda_fp16_h_abspath and cuda_fp16_hpp_abspath:
        path = os.path.dirname(cuda_fp16_h_abspath)
        if path != os.path.dirname(cuda_fp16_hpp_abspath):
            KeOps_Error("cuda_fp16.h and cuda_fp16.hpp are not in the same folder !")
        path += os.path.sep
        return path
    else:
        KeOps_Error("cuda_fp16.h and cuda_fp16.hpp were not found")
        

def get_cuda_version():
    cuda = ctypes.CDLL(find_library("cudart"))
    cuda_version = ctypes.c_int()
    cuda.cudaDriverGetVersion(ctypes.byref(cuda_version))
    cuda_version = int(cuda_version.value)
    cuda_version_major = cuda_version//1000
    cuda_version_minor = (cuda_version-(1000*cuda_version_major))//10
    return f"{cuda_version_major}.{cuda_version_minor}"
    
def get_gpu_props():
    """
    Return number of GPU by reading libcuda.
    Here we assume the system has cuda support (more precisely that libcuda can be loaded)
    Adapted from https://gist.github.com/f0k/0d6431e3faa60bffc788f8b4daa029b1
    credit: Jan Schlüter
    """
    cuda = ctypes.CDLL(find_library("cuda"))

    nGpus = ctypes.c_int()
    error_str = ctypes.c_char_p()

    result = cuda.cuInit(0)
    if result != CUDA_SUCCESS:
        # cuda.cuGetErrorString(result, ctypes.byref(error_str))
        # KeOps_Warning("cuInit failed with error code %d: %s" % (result, error_str.value.decode()))
        KeOps_Warning(
            "cuda was detected, but driver API could not be initialized. Switching to cpu only."
        )
        return 0, ""

    result = cuda.cuDeviceGetCount(ctypes.byref(nGpus))
    if result != CUDA_SUCCESS:
        # cuda.cuGetErrorString(result, ctypes.byref(error_str))
        # KeOps_Warning("cuDeviceGetCount failed with error code %d: %s" % (result, error_str.value.decode()))
        KeOps_Warning(
            "cuda was detected, driver API has been initialized, but no working GPU has been found. Switching to cpu only."
        )
        return 0, ""

    nGpus = nGpus.value

    def safe_call(d, result):
        test = result == CUDA_SUCCESS
        if not test:
            KeOps_Warning(
                f"""
                    cuda was detected, driver API has been initialized, 
                    but there was an error for detecting properties of GPU device nr {d}. 
                    Switching to cpu only.
                """
            )
        return test

    test = True
    MaxThreadsPerBlock = [0] * (nGpus)
    SharedMemPerBlock = [0] * (nGpus)
    for d in range(nGpus):

        # getting handle to cuda device
        device = ctypes.c_int()
        result &= safe_call(d, cuda.cuDeviceGet(ctypes.byref(device), ctypes.c_int(d)))

        # getting MaxThreadsPerBlock info for device
        output = ctypes.c_int()
        result &= safe_call(
            d,
            cuda.cuDeviceGetAttribute(
                ctypes.byref(output),
                ctypes.c_int(CU_DEVICE_ATTRIBUTE_MAX_THREADS_PER_BLOCK),
                device,
            ),
        )
        MaxThreadsPerBlock[d] = output.value

        # getting SharedMemPerBlock info for device
        result &= safe_call(
            d,
            cuda.cuDeviceGetAttribute(
                ctypes.byref(output),
                ctypes.c_int(CU_DEVICE_ATTRIBUTE_MAX_SHARED_MEMORY_PER_BLOCK),
                device,
            ),
        )
        SharedMemPerBlock[d] = output.value

    # Building compile flags in the form "-D..." options for further compilations
    # (N.B. the purpose is to avoid the device query at runtime because it would slow down computations)
    string_flags = f"-DMAXIDGPU={nGpus-1} "
    for d in range(nGpus):
        string_flags += f"-DMAXTHREADSPERBLOCK{d}={MaxThreadsPerBlock[d]} "
        string_flags += f"-DSHAREDMEMPERBLOCK{d}={SharedMemPerBlock[d]} "

    if test:
        return nGpus, string_flags
    else:
        return 0, 0, ""
