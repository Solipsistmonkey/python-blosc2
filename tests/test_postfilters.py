########################################################################
#
#       Author:  The Blosc development team - blosc@blosc.org
#
########################################################################

import pytest

import blosc2
import numpy as np


@pytest.mark.parametrize("func, input_dtype, output_dtype, start",
                         [
                            ("postf1", np.dtype(np.int32), None, 0),
                            ("postf1", np.dtype(np.int32), np.dtype(np.float32), 0),
                            ("postf2", np.dtype(np.complex128), None, 0),
                            ("postf2", np.dtype(np.float64), None, None),
                            ("postf3", np.dtype("M8[D]"), np.dtype(np.int64), None),
                         ])
@pytest.mark.parametrize(
    "cparams, dparams, nchunks, contiguous, urlpath",
    [
        ({"codec": blosc2.Codec.LZ4, "clevel": 6}, {"nthreads": 1}, 2, True, None),
        ({}, {"nthreads": 2}, 1, True, "test_postfilters.b2frame"),
        (
                {"splitmode": blosc2.SplitMode.ALWAYS_SPLIT, "nthreads": 4},
                {"schunk": None, "nthreads": 4},
                5,
                False,
                None
        ),
        ({"codec": blosc2.Codec.LZ4HC}, {"nthreads": 4}, 3, False, "test_postfilters.b2frame"),
    ],
)
def test_postfilters(contiguous, urlpath, cparams, dparams, nchunks, func, input_dtype, output_dtype, start):
    blosc2.remove_urlpath(urlpath)

    output_dtype = input_dtype if output_dtype is None else output_dtype
    chunk_len = 2_000
    data = np.arange(0, chunk_len * nchunks, dtype=input_dtype)
    schunk = blosc2.SChunk(chunksize=chunk_len * input_dtype.itemsize, data=data,
                           contiguous=contiguous, urlpath=urlpath, cparams=cparams, dparams=dparams,
                           typesize=input_dtype.itemsize)
    if func == "postf1":
        @blosc2.postfilter(schunk, input_dtype, output_dtype)
        def postf1(input, output, start):
            for i in range(input.size):
                output[i] = start + i
    elif func == "postf2":
        @blosc2.postfilter(schunk, input_dtype, output_dtype)
        def postf2(input, output, start):
            output[:] = input - np.pi
    else:
        @blosc2.postfilter(schunk, input_dtype, output_dtype)
        def postf3(input, output, start):
            output[:] = input <= np.datetime64('1997-12-31')

    post_data = np.empty(chunk_len * nchunks, dtype=output_dtype)
    schunk.get_slice(0, chunk_len * nchunks, out=post_data)

    res = np.empty(chunk_len * nchunks, dtype=output_dtype)
    locals()[func](data, res, start)
    if "f" in input_dtype.str:
        assert np.allclose(post_data, res)
    else:
        assert np.array_equal(post_data, res)

    blosc2.remove_urlpath(urlpath)
