function buatTitik(waktu, overrides = {}) {
  return {
    local_datetime: waktu,
    t: 28,
    hu: 78,
    weather_desc: 'Cerah Berawan',
    ws: 5,
    wd: 'E',
    tcc: 30,
    tp: 0,
    vs_text: '> 10 km',
    ...overrides,
  };
}

function buatResponsBmkg(points) {
  return {
    lokasi: {
      desa: 'Aikmel',
      kecamatan: 'Aikmel',
      kotkab: 'Lombok Timur',
      provinsi: 'Nusa Tenggara Barat',
      lat: -8.6,
      lon: 116.5,
    },
    data: [{ cuaca: [points] }],
  };
}

module.exports = { buatTitik, buatResponsBmkg };
