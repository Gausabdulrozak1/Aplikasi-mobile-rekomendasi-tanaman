# Local ML Hardware Report

Measured at: `2026-08-13T23:43:56.0961007+08:00`

## System

| Item | Measured value |
| --- | --- |
| Laptop | HP Laptop 14s-fq1xxx |
| OS | Microsoft Windows 11 Home Single Language, 64-bit |
| OS version/build | 10.0.26200 / 26200 |
| DirectX | DirectX 12 |
| CPU | AMD Ryzen 3 5300U with Radeon Graphics |
| CPU topology | 4 physical cores, 8 logical processors |
| Python | 3.11.9 |
| Python executable | `C:\Users\azulf\AppData\Local\Programs\Python\Python311\python.exe` |

## Memory

| Item | Measured value |
| --- | ---: |
| Installed label from DxDiag | 8192 MB RAM |
| Total visible physical memory | 7,866,884,096 bytes (7.327 GiB) |
| Available memory at audit | 883,789,824 bytes (0.823 GiB) |
| Memory pressure at audit | High |

The installed 8 GB is not fully visible to Windows because the integrated GPU
and firmware reserve part of system memory. The available-memory value is a
point-in-time measurement and can change as applications open or close.

## Graphics

| Item | Measured value |
| --- | --- |
| GPU | AMD Radeon(TM) Graphics |
| Processor/device | AMD Radeon Graphics Processor `0x164C` |
| Display memory | 4246 MiB |
| Dedicated memory | 495 MiB |
| Shared memory | 3751 MiB |
| WMI adapter RAM | 536,870,912 bytes (0.5 GiB) |
| Driver | 31.0.12044.3, dated 2022-10-25 |
| Current display | 1920x1080 |

Integrated shared GPU memory is borrowed from the same limited physical RAM; it
is not equivalent to dedicated VRAM.

## Storage

| Item | Measured value |
| --- | ---: |
| D: total | 90,056,945,664 bytes (83.872 GiB) |
| D: free | 76,101,218,304 bytes (70.875 GiB) |

Disk capacity is sufficient for the isolated environment and a model cache,
but RAM is currently the dominant constraint.

## ROCm/HIP Decision

`ROCM_SUPPORTED = false`

AMD states that hardware absent from its Windows-supported GPU/APU table is not
officially supported. Ryzen 3 5300U / Radeon device `0x164C` is absent; only
newer selected Radeon and Ryzen AI hardware is listed. No ROCm/HIP installation
was attempted.

Source: [AMD Windows system requirements](https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/shared/hipsdk/reference/system-requirements.html)

## DirectML Gate

The DirectX 12 prerequisite is met, so a minimal DirectML backend test is
permitted. This is not proof that Stable Diffusion training operators work.
Microsoft marks DirectML as maintenance mode and the installed AMD display
driver dates from 2022, so actual forward/backward tests remain mandatory.

Source: [Microsoft DirectML](https://github.com/microsoft/DirectML)

## Safety Decision

Do not load Stable Diffusion 1.5 while available RAM remains near 0.823 GiB.
Proceed only with isolated-environment installation and a very small tensor
DirectML check. Model loading requires a separate memory gate.
