#!/usr/bin/env python
# wujian@2018

import os
import sys
import glob
import warnings
import librosa as audio_lib
import numpy as np

import libs.iobase as io
from libs.utils import stft, read_wav, get_logger

logger = get_logger(__name__)

__all__ = [
    "ArchiveReader",
    "ArchiveWriter",
    "SpectrogramReader",
    "ScriptReader",
    "WaveReader",
    "NumpyReader",
]


def ext_fopen(fname, mode):
    """
    Extend file open function, support "-", which means std-input/output
    """
    if mode not in ["w", "r", "wb", "rb"]:
        raise ValueError("Unknown open mode: {mode}".format(mode=mode))
    if not fname:
        return None
    if fname == "-":
        if mode in ["w", "wb"]:
            return sys.stdout.buffer if mode == "wb" else sys.stdout
        else:
            return sys.stdin.buffer if mode == "rb" else sys.stdin
    else:
        if not os.path.exists(fname):
            raise FileNotFoundError("Could not find {f}".format(f=fname))
        return open(fname, mode)


def ext_fclose(fname, fd):
    """
    Extend file close function, support "-", which means std-input/output
    """
    if fname != "-" and fd:
        fd.close()


def parse_scps(scp_path, addr_processor=lambda x: x):
    """
    Parse kaldi's script(.scp) file with supported for stdin
    WARN: last line of scripts could not be None and with "\n" end
    """
    scp_dict = dict()
    f = ext_fopen(scp_path, 'r')
    for scp in f:
        scp_tokens = scp.strip().split()
        if len(scp_tokens) != 2:
            raise RuntimeError("Error format of context \'{}\'".format(scp))
        key, addr = scp_tokens
        if key in scp_dict:
            raise ValueError("Duplicate key \'{}\' exists!".format(key))
        scp_dict[key] = addr_processor(addr)
    ext_fclose(scp_path, f)
    return scp_dict


class Reader(object):
    """
        Base class for sequential/random accessing, to be implemented
    """

    def __init__(self, scp_path, addr_processor=lambda x: x):
        self.index_dict = parse_scps(scp_path, addr_processor=addr_processor)
        self.index_keys = [key for key in self.index_dict.keys()]

    def _load(self, key):
        raise NotImplementedError

    # number of utterance
    def __len__(self):
        return len(self.index_dict)

    # avoid key error
    def __contains__(self, key):
        return key in self.index_dict

    # sequential index
    def __iter__(self):
        for key in self.index_keys:
            yield key, self._load(key)

    # random index, support str/int as index
    def __getitem__(self, index):
        if type(index) == int:
            num_utts = len(self.index_keys)
            if index >= num_utts or index < 0:
                raise KeyError("Interger index out of range, {} vs {}".format(
                    index, num_utts))
            key = self.index_keys[index]
            return self._load(key)
        elif type(index) is str:
            if index not in self.index_dict:
                raise KeyError("Missing utterance {}!".format(index))
            return self._load(index)
        else:
            raise IndexError("Unsupported index type: {}".format(type(index)))


class Writer(object):
    """
        Base Writer class to be implemented
    """

    def __init__(self, ark_path, scp_path=None):
        self.scp_path = scp_path
        self.ark_path = ark_path
        # if dump ark to output, then ignore scp
        if ark_path == "-" and scp_path:
            warnings.warn(
                "Ignore .scp output discriptor cause dump archives to stdout")
            self.scp_path = None

    def __enter__(self):
        # "wb" is important
        self.ark_file = ext_fopen(self.ark_path, "wb")
        self.scp_file = ext_fopen(self.scp_path, "w")
        return self

    def __exit__(self, *args):
        ext_fclose(self.ark_path, self.ark_file)
        ext_fclose(self.scp_path, self.scp_file)

    def write(self, key, data):
        raise NotImplementedError


class ArchiveReader(object):
    """
        Sequential Reader for Kalid's archive(.ark) object
    """

    def __init__(self, ark_path):
        if not os.path.exists(ark_path):
            raise FileNotFoundError("Could not find {}".format(ark_path))
        self.ark_path = ark_path

    def __iter__(self):
        with open(self.ark_path, "rb") as fd:
            for key, mat in io.read_ark(fd):
                yield key, mat


class WaveReader(Reader):
    """
        Sequential/Random Reader for single/multiple channel wave
        Format of wav.scp follows Kaldi's definition:
            key1 /path/to/wav
            ...

        And /path/to/wav allowed to be a pattern, for example:
            key1 /home/data/key1.CH*.wav
        /home/data/key1.CH*.wav matches file /home/data/key1.CH{1,2,3..}.wav 
    """

    def __init__(self, wav_scp, sample_rate=None, normalize=True):
        super(WaveReader, self).__init__(wav_scp)
        self.samp_rate = sample_rate
        self.normalize = normalize

    def _query_flist(self, key):
        flist = glob.glob(self.index_dict[key])
        if not len(flist):
            raise RuntimeError(
                "Could not find file matches template \'{}\'".format(
                    self.index_dict[key]))
        return flist

    def _read_s(self, addr):
        # return C x N or N
        samp_rate, samps = read_wav(
            addr, normalize=self.normalize, return_rate=True)
        # if given samp_rate, check it
        if self.samp_rate is not None and samp_rate != self.samp_rate:
            raise RuntimeError("SampleRate mismatch: {:d} vs {:d}".format(
                samp_rate, self.samp_rate))
        return samps

    def _read_m(self, key):
        # return C x N matrix or N vector
        wav_list = self._query_flist(key)
        if len(wav_list) == 1:
            return self._read_s(wav_list[0])
        else:
            # in sorted order, sentitive to beamforming
            return np.vstack([self._read_s(addr) for addr in sorted(wav_list)])

    def _load(self, key):
        return self._read_m(key)

    def samp_norm(self, key):
        samps = self._load(key)
        return np.max(np.abs(samps))

    def duration(self, key):
        samps = self._load(key)
        return samps.shape[-1] / self.samp_rate

class NumpyReader(Reader):
    """
        Sequential/Random Reader for numpy's ndarray(*.npy) file
    """

    def __init__(self, npy_scp):
        super(NumpyReader, self).__init__(npy_scp)

    def _load(self, key):
        return np.load(self.index_dict[key])


class SpectrogramReader(WaveReader):
    """
        Sequential/Random Reader for single/multiple channel STFT
    """

    def __init__(self, wav_scp, normalize=True, **kwargs):
        super(SpectrogramReader, self).__init__(wav_scp, normalize=normalize)
        self.stft_kwargs = kwargs

    def _load(self, key):
        # get wave samples
        samps = super()._read_m(key)
        if samps.ndim == 1:
            return stft(samps, **self.stft_kwargs)
        else:
            N, _ = samps.shape
            # stft need input to be contiguous in memory
            # make samps.flags['C_CONTIGUOUS'] = True
            samps = np.ascontiguousarray(samps)
            return np.stack(
                [stft(samps[c], **self.stft_kwargs) for c in range(N)])


class ScriptReader(Reader):
    """
        Reader for kaldi's scripts(for BaseFloat matrix)
    """

    def __init__(self, ark_scp):
        def addr_processor(addr):
            addr_token = addr.split(":")
            if len(addr_token) == 1:
                raise ValueError("Unsupported scripts address format")
            path, offset = ":".join(addr_token[0:-1]), int(addr_token[-1])
            return (path, offset)

        super(ScriptReader, self).__init__(
            ark_scp, addr_processor=addr_processor)

    def _load(self, key):
        path, offset = self.index_dict[key]
        with open(path, 'rb') as f:
            f.seek(offset)
            io.expect_binary(f)
            ark = io.read_general_mat(f)
        return ark


class ArchiveWriter(Writer):
    """
        Writer for kaldi's scripts && archive(for BaseFloat matrix)
    """

    def __init__(self, ark_path, scp_path=None):
        if not ark_path:
            raise RuntimeError("Seem configure path of archives as None")
        super(ArchiveWriter, self).__init__(ark_path, scp_path)
        self.abs_path = os.path.abspath(self.ark_path)

    def write(self, key, matrix):
        io.write_token(self.ark_file, key)
        io.write_binary_symbol(self.ark_file)
        io.write_common_mat(self.ark_file, matrix)
        if self.scp_file:
            offset = self.ark_file.tell()
            self.scp_file.write("{key}\t{path}:{offset}\n".format(
                key=key, path=self.abs_path, offset=offset))


def test_archive_writer(ark, scp):
    with ArchiveWriter(ark, scp) as writer:
        for i in range(10):
            mat = np.random.rand(100, 20)
            writer.write("mat-{:d}".format(i), mat)
    print("TEST *test_archive_writer* DONE!")


def test_script_reader(egs):
    scp_reader = ScriptReader(egs)
    for key, mat in scp_reader:
        print("{}: {}".format(key, mat.shape))
    print("TEST *test_script_reader* DONE!")


if __name__ == "__main__":
    test_archive_writer("egs.ark", "egs.scp")
    test_script_reader("egs.scp")
