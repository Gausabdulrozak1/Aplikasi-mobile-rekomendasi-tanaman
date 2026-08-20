# Local Mock API Smoke Test

This test follows the production application path while keeping Stable
Diffusion off the laptop:

```text
Flutter -> Express -> FastAPI mock -> Express image proxy -> Flutter
```

Start FastAPI mock in terminal 1:

```powershell
cd D:\TaniAdaptif
$env:INFERENCE_PROVIDER = "mock"
.\.venv\Scripts\python.exe -m uvicorn inference_api.app.main:app --host 127.0.0.1 --port 5000
```

Start Express in terminal 2:

```powershell
cd D:\TaniAdaptif\backend-nodejs
npm start
```

Check the public backend boundary:

```powershell
Invoke-RestMethod http://localhost:3000/api/kesehatan
Invoke-RestMethod http://localhost:3000/api/visual/ready
Invoke-RestMethod http://localhost:3000/api/visual/model-info
```

Generate a labelled placeholder through Express:

```powershell
$body = @{
  crop = "padi"
  land_type = "sawah"
  water_availability = "cukup"
  previous_crop = "jagung"
  weather_summary = "Cerah berawan; suhu 28 C"
  seed = 42
  request_id = "powershell-smoke-001"
  steps = 5
  width = 512
  height = 512
} | ConvertTo-Json

$result = Invoke-RestMethod -Method Post `
  -Uri http://localhost:3000/api/visual/generate `
  -ContentType "application/json" `
  -Body $body
$result
Invoke-WebRequest -Uri $result.image_url -OutFile artifacts\test_reports\local_mock_proxy.png
```

Expected metadata: `provider=mock`, `is_mock=true`,
`delivery_path=backend_proxy`, and `upstream_image_url_exposed=false`.

For an Android emulator, run:

```powershell
cd D:\TaniAdaptif\mobile-flutter\tani_adaptif
flutter run --dart-define-from-file=config/development.example.json
```

The recommendation must remain visible if inference is stopped. Mock output is
a UI/contract check only and is never real model or quality evidence.
