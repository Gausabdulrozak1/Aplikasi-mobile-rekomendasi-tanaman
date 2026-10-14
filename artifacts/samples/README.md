# Samples

Folder ini untuk sampel kecil yang aman disimpan di repository, seperti contoh
prompt, contoh metadata, atau template non-rahasia.

Jangan simpan:

- gambar dataset publik dalam jumlah besar;
- hasil generated image;
- model `.safetensors`;
- token atau credential.

Untuk generated image, gunakan folder runtime yang sudah diabaikan Git:

```text
inference_api/generated/
artifacts/samples/generated/
```

