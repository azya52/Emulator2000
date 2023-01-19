OFFSET = 982

cityes = [
    {
        "name": "ABIDJN",
        "lat": 5.3,
        "lon": -4.0,
        "tz": 0,
        "kibla": 80,
    }, {
        "name": "ACCRA",
        "lat": 5.6,
        "lon": -0.2,
        "tz": 0,
        "kibla": 70,
    }, {
        "name": "AKLAND",
        "lat": -36.8,
        "lon": 174.8,
        "tz": 13,
        "kibla": 240,
    }, {
        "name": "BOSTON",
        "lat": 42.4,
        "lon": -71.1,
        "tz": -5,
        "kibla": 80,
    }, {
        "name": "CAIRO",
        "lat": 30.0,
        "lon": 31.2,
        "tz": 2,
        "kibla": 130,
    }, {
        "name": "IZMIR",
        "lat": 38.4,
        "lon": 27.1,
        "tz": 3,
        "kibla":140,
    }, {
        "name": "KARACH",
        "lat": 24.9,
        "lon": 67,
        "tz": 5,
        "kibla": 260,
    }, {
        "name": "K^LMPR",
        "lat": 3.1,
        "lon": 101.7,
        "tz": 8.0,
        "kibla": 290,
    }, {
        "name": "LAGOS",
        "lat": 6.5,
        "lon": 3.4,
        "tz": 1,
        "kibla": 70,
    }, {
        "name": "LAHORE",
        "lat": 31.6,
        "lon": 74.3,
        "tz": 5,
        "kibla": 260,
    }, {
        "name": "LONDON",
        "lat": 51.5,
        "lon": -0.1,
        "tz": 0,
        "kibla": 120,
    }
    #original size ~114
]

with open("assets/spacetronic.ram","wb") as file:
    file.seek(2036)
    file.write(bytes([1]))
    file.seek(OFFSET)

    for city in cityes:
        shift = 3
        count = 0
        name = [0,0,0,0]
        for char in city["name"]:
            code = ord(char) - ord("A") + 1
            if (shift >= 0):
                name[count] += (code << shift) & 0xFF
            if (shift < 0):
                name[count] += code >> abs(shift)
                count += 1
                shift += 8
                name[count] = (code << shift) & 0xFF
            shift -= 5

        lat = int(city["lat"])
        if (lat < 0):
            lat = 80 + abs(lat)
        lat = (((lat // 10) << 4) | (lat % 10)) & 0xFF
        lat_frac = int(abs(city["lat"]) * 10 % 10)

        tz = int(city["tz"])
        if (tz < 0):
            tz = 20 + abs(tz)
        tz = (((tz // 10 % 10) << 4) | (tz % 10)) & 0xFF

        lon_cor = round(city["lon"] - (city["tz"] * 15), 1)
        lon = int(lon_cor)
        if (lon_cor < 0):
            lon = 80 + abs(lon)
        lon_d = lon // 10
        lon = lon % 10
        lon_frac = int(abs(lon_cor) * 10 % 10)

        tz_frac = int(abs(city["tz"]) * 100 % 100)
        if (tz_frac == 50):
            tz_frac = 1
        elif (tz_frac == 73):
            tz_frac = 2
        elif (tz_frac == 75):
            tz_frac = 3

        kibla = (city["kibla"] // 100 << 4) | city["kibla"] // 10 % 10

        file.write(bytes(
            name + [
            lat,
            (lat_frac << 4) | lon_d,
            (lon << 4) | lon_frac,
            (tz_frac << 6) | tz,
            kibla & 0xFF
        ]))