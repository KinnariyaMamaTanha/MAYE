import os

import torch


def _get_local_rank() -> int | None:
    """Function that gets the local rank from the environment.

    Returns:
        local_rank int or None if not set.
    """
    local_rank = os.environ.get("LOCAL_RANK")
    if local_rank is not None:
        local_rank = int(local_rank)
    return local_rank


def _setup_cuda_device(device: torch.device) -> torch.device:
    """Function that sets the CUDA device and infers the cuda
    index if not set.

    Args:
        device (torch.device): The device to set.

    Raises:
        RuntimeError: If device index is not available.

    Returns:
        device
    """
    local_rank = _get_local_rank() or 0
    if not device.index:
        device = torch.device(type="cuda", index=local_rank)

    # Ensure index is available before setting device
    if device.index >= torch.cuda.device_count():
        raise RuntimeError(
            "The local rank is larger than the number of available GPUs."
        )

    torch.cuda.set_device(device)
    return device


def _get_device_type_from_env() -> str:
    """Function that gets the torch.device based on the current machine.

    This currently only supports CPU, CUDA.

    Returns:
        device
    """
    if torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cpu"
    return device


def _validate_device_from_env(device: torch.device) -> None:
    """Function that validates the device is correct given the current machine.
    This will raise an error if the device is not available or doesn't match the
    assigned process device on distributed runs.

    Args:
        device (torch.device): The device to validate.

    Raises:
        RuntimeError: If the device is not available or doesn't match the assigned process device.

    Returns:
        device
    """
    local_rank = _get_local_rank()

    # Check if the device index is correct
    if device.type == "cuda" and local_rank is not None:
        # Ensure device index matches assigned index when distributed training
        if device.index != local_rank:
            raise RuntimeError(
                f"You can't specify a device index when using distributed training. \
                Device specified is {device} but was assigned cuda:{local_rank}"
            )

    # Check if the device is available on this machine
    try:
        torch.empty(0, device=device)
    except RuntimeError as e:
        raise RuntimeError(
            f"The device {device} is not available on this machine."
        ) from e


def get_device(device: str | None) -> torch.device:
    """Function that takes an optional device string, verifies it's correct and available given the machine and
    distributed settings, and returns a torch.device. If device string is not provided, this function will
    infer the device based on the environment.

    If CUDA is available and being used, this function also sets the CUDA device.

    Args:
        device (Optional[str]): The name of the device to use.

    Returns:
        torch.device: device.
    """
    if device is None:
        device = _get_device_type_from_env()
    torch_device = torch.device(device)
    if torch_device.type == "cuda":
        torch_device = _setup_cuda_device(torch_device)
    _validate_device_from_env(torch_device)
    return torch_device


def get_visible_device(index: int) -> int:
    devices = list(range(torch.cuda.device_count()))

    if not devices:
        raise RuntimeError("No CUDA devices available.")

    try:
        return devices[index]
    except IndexError:
        raise ValueError(
            f"Error: Index {index} out of range. Available logical devices: {devices}"
        )
