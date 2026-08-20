# User Guide

## Get a Recommendation

1. Open TaniAdaptif and refresh the weather card if needed.
2. Check the BMKG source, timestamp, and any cache warning.
3. Open the recommendation form.
4. Select previous crop, water availability, and land type.
5. Submit the form and review the ordered crops, rule reason, four-week plan,
   weather projection note, and planting schedule.

When the phone is offline, the app can show the last stored weather and the last
recommendation for exactly the same form inputs. It labels this as cache data.

## Visual Simulation

On a recommendation result, request a visual simulation. The recommendation is
already complete before this step. During generation the app shows an
indeterminate progress state. A successful result shows the model/provider,
seed, request ID, and server-built prompt. A failure leaves every recommendation
section visible and offers a retry.

Mock visuals are development placeholders, not crop forecasts, agronomic proof,
or research evaluation output. Stable Diffusion/LoRA does not choose the crop.

## Common Problems

- Backend unavailable: start Express on port 3000 or confirm the configured URL.
- Visual unavailable: start mock FastAPI on port 5000; recommendation remains usable.
- Android emulator cannot reach localhost: use `10.0.2.2` (the development
  example already does this).
- Physical phone cannot connect: use the workstation LAN IP and confirm both
  devices share a trusted network; do not disable Windows security controls.
- Missing rainfall: wait for complete BMKG precipitation data or use the manual
  category endpoint; the app does not assume missing rain equals zero.
