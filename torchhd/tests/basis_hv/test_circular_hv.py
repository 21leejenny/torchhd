import pytest
import torch

import torchhd
from torchhd import functional
from torchhd import HRR

from ..utils import torch_dtypes, supported_dtype, vsa_models

seed = 2147483644


class TestCircular_hv:
    @pytest.mark.parametrize("n", [1, 3, 55])
    @pytest.mark.parametrize("d", [84, 10])
    @pytest.mark.parametrize("model", vsa_models)
    def test_shape(self, n, d, model):
        if model == HRR:
            return

        hv = functional.circular_hv(n, d, model)

        assert hv.dim() == 2
        assert hv.size(0) == n
        assert hv.size(1) == d

    @pytest.mark.parametrize("model", vsa_models)
    def test_generator(self, model):
        if model == HRR:
            return

        generator = torch.Generator()
        generator.manual_seed(seed)
        hv1 = functional.circular_hv(20, 10000, model, generator=generator)

        generator = torch.Generator()
        generator.manual_seed(seed)

        hv2 = functional.circular_hv(20, 10000, model, generator=generator)
        assert torch.all(hv1 == hv2).item()

    @pytest.mark.parametrize("dtype", torch_dtypes)
    @pytest.mark.parametrize("model", vsa_models)
    def test_value(self, dtype, model):

        if not supported_dtype(dtype, model):
            with pytest.raises(ValueError):
                functional.circular_hv(3, 26, model, dtype=dtype)

            return

        if model == HRR:
            with pytest.raises(ValueError):
                functional.circular_hv(3, 26, model, dtype=dtype)

            return

        generator = torch.Generator()
        generator.manual_seed(seed)

        hv = functional.circular_hv(50, 26000, model, dtype=dtype, generator=generator)
        assert hv.requires_grad == False
        assert hv.dim() == 2
        assert hv.size(0) == 50
        assert hv.size(1) == 26000

        if model == torchhd.BSC:
            assert torch.all((hv == False) | (hv == True)).item()

        elif model == torchhd.MAP:
            assert torch.all((hv == -1) | (hv == 1)).item()

        elif model == torchhd.HRR:
            std, mean = torch.std_mean(hv)
            assert torch.allclose(
                mean, torch.tensor(0.0, dtype=mean.dtype), atol=0.0001
            )

        elif model == torchhd.FHRR:
            mag = hv.abs()
            assert torch.allclose(mag, torch.tensor(1.0, dtype=mag.dtype))

        hv = functional.circular_hv(8, 1000000, model, generator=generator, dtype=dtype)
        sims = functional.cos_similarity(hv[0], hv)
        sims_diff = sims[:-1] - sims[1:]
        assert torch.all(
            sims_diff.sign() == torch.tensor([1, 1, 1, 1, -1, -1, -1])
        ), "second half must get more similar"

        assert torch.allclose(
            sims_diff.abs(), torch.tensor(0.25, dtype=sims_diff.dtype), atol=0.005
        ), "similarity decreases linearly"

    @pytest.mark.parametrize("sparsity", [0.0, 0.1, 0.756, 1.0])
    @pytest.mark.parametrize("dtype", torch_dtypes)
    def test_sparsity(self, sparsity, dtype):
        if not supported_dtype(dtype, torchhd.BSC):
            return

        generator = torch.Generator()
        generator.manual_seed(seed)

        hv = functional.circular_hv(
            1000,
            10000,
            torchhd.BSC,
            generator=generator,
            dtype=dtype,
            sparsity=sparsity,
        )

        calc_sparsity = torch.sum(hv == False).div(10000 * 1000)
        assert torch.allclose(calc_sparsity, torch.tensor(sparsity), atol=0.005)

    @pytest.mark.parametrize("dtype", torch_dtypes)
    def test_device(self, dtype):
        if not supported_dtype(dtype):
            return

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        hv = functional.circular_hv(3, 52, device=device, dtype=dtype)
        assert hv.device == device

    @pytest.mark.parametrize("dtype", torch_dtypes)
    @pytest.mark.parametrize("model", vsa_models)
    def test_device(self, dtype, model):
        if not supported_dtype(dtype, model):
            return

        if model == HRR:
            return

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        hv = functional.circular_hv(3, 52, model, device=device, dtype=dtype)
        assert hv.device == device

    def test_uses_default_dtype(self):
        hv = functional.circular_hv(3, 52, torchhd.BSC)
        assert hv.dtype == torch.bool

        torch.set_default_dtype(torch.float32)
        hv = functional.circular_hv(3, 52, torchhd.MAP)
        assert hv.dtype == torch.float32
        # hv = functional.circular_hv(3, 52, torchhd.HRR)
        # assert hv.dtype == torch.float32

        torch.set_default_dtype(torch.float64)
        hv = functional.circular_hv(3, 52, torchhd.MAP)
        assert hv.dtype == torch.float64
        # hv = functional.circular_hv(3, 52, torchhd.HRR)
        # assert hv.dtype == torch.float64

        hv = functional.circular_hv(3, 52, torchhd.FHRR)
        assert hv.dtype == torch.complex64

    def test_requires_grad(self):
        hv = functional.circular_hv(3, 52, torchhd.MAP, requires_grad=True)
        assert hv.requires_grad == True

        # hv = functional.circular_hv(3, 52, torchhd.HRR, requires_grad=True)
        # assert hv.requires_grad == True

        hv = functional.circular_hv(3, 52, torchhd.FHRR, requires_grad=True)
        assert hv.requires_grad == True
