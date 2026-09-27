# GPU Setup for StyleScape

The real four-image pipeline uses SDXL img2img with Canny + Depth ControlNet.
It needs CUDA-enabled PyTorch. CPU-only PyTorch will not work for practical use.

Your current machine has an NVIDIA GTX 1650, but the installed venv currently
uses CPU-only PyTorch.

## Required Steps

1. Update the NVIDIA driver from NVIDIA's website.
   - Your current driver is `457.34`, which is too old for modern CUDA PyTorch.
   - Install a current Game Ready or Studio Driver.

2. Reopen PowerShell in this project folder.

3. Install CUDA PyTorch:

```powershell
.\setup_cuda_torch.ps1
```

4. Confirm the script prints:

```text
cuda available: True
gpu: NVIDIA GeForce GTX 1650
```

5. Run the app:

```powershell
.\venv\Scripts\python.exe app.py
```

## Low VRAM Note

GTX 1650 has 4 GB VRAM. The app automatically switches SDXL ControlNet to
lower-VRAM settings: 640px generation, model CPU offload, attention slicing,
VAE slicing, and VAE tiling.
