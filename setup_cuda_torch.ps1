$ErrorActionPreference = "Stop"

Write-Host "Checking NVIDIA GPU..."
nvidia-smi

Write-Host ""
Write-Host "Installing CUDA-enabled PyTorch into this venv..."
Write-Host "Important: update your NVIDIA driver first if it is older than 522.xx."

.\venv\Scripts\python.exe -m pip uninstall -y torch torchvision torchaudio
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

Write-Host ""
Write-Host "Verifying CUDA from Python..."
.\venv\Scripts\python.exe -c "import torch; print('torch:', torch.__version__); print('cuda available:', torch.cuda.is_available()); print('cuda version:', torch.version.cuda); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
