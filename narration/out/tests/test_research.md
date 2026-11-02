# Test run: dramaturg research, Globalist from Paris

A test of the `## Research` step in `dramaturg.md`, on the first 20 of the 184 stations of `runs/h2910_globalist_paris_s0` (steps 0–494 of 5,000).

**Result:** 6 stations have a source matching place and time, 7 have a partial one, and 7 are "No conclusive information found". Only 5 of the 13 stations with a source document any satellite use, and none ties a decision to the image the agent actually saw.

## Method

- **Stations:** the walk is cut wherever a step is longer than 30 km, the same rule as "places" in `analysis/h2910_compare.py`. A station's location is the median latitude and longitude of its visits.
- **Date:** the acquisition date of the tile nearest that median, from `data/global/index.parquet`. The range of dates across the station's tiles is given as well.
- **Place names:** reverse geocoding with OpenStreetMap Nominatim. It returned nothing for open ocean, so those labels are my own reading of the coordinates.
- **Search:** at least one web search per station, with a second, narrower one for nine stations. Every cited claim was checked on its source page. Claims whose pages couldn't be read are listed under "Unverified leads" and not used.

**Evidence grades** (added for this test, not in the spec):

- **Match:** the source names the station's town, county or a named nearby feature, and falls within about a year of the tile.
- **Partial:** the source covers only a wider region, or is dated further from the tile.
- **None:** nothing relevant found.

"Satellite use" says whether the source documents satellites being used. Distances marked "my estimate" use coordinates I supplied, not the source's.

## Overview

| # | Place | Tile date | Cover | Evidence | Satellite use |
|---|---|---|---|---|---|
| 0 | Champigny-sur-Marne, France | 2017-03-27 | land | Match | yes (radar) |
| 1 | Kivalliq Region, Nunavut, Canada | 2023-08-07 | land | None | – |
| 2 | Jutaí, Amazonas, Brazil | 2020-08-02 | land | Partial | yes |
| 3 | Northern South China Sea | 2022-08-26 | ocean | Partial | no |
| 4 | Southern Ocean near Cape Horn | 2023-01-06 | ocean | None | – |
| 5 | Tropical North Atlantic | 2022-10-08 | ocean | None | – |
| 6 | South Atlantic near Ascension Island | 2023-05-30 | ocean | Partial | yes |
| 7 | Unorganized Borough, Alaska, USA | 2020-04-11 | land | None | – |
| 8 | Tallapoosa County, Alabama, USA | 2019-04-10 | land | None | – |
| 9 | Méridja, Béchar, Algeria | 2016-03-02 | land | Match | no |
| 10 | Bay of Bengal off Andhra Pradesh, India | 2021-05-30 | ocean | Partial | no |
| 11 | Zhegu, Tsomei County, Tibet, China | 2022-12-12 | land | Match | no |
| 12 | Khafsa, Aleppo Governorate, Syria | 2023-01-27 | land | Partial | no |
| 13 | Inland Western Australia | 2020-04-25 | land | None | – |
| 14 | Chernoyarsky district, Astrakhan, Russia | 2020-09-01 | land | None | – |
| 15 | Dongfang, Hainan, China | 2022-03-26 | coast | Match | no |
| 16 | El Mina, Nouakchott, Mauritania | 2018-12-09 | coast | Partial | yes |
| 17 | Antofagasta de la Sierra, Catamarca, Argentina | 2021-11-24 | land | Match | yes (radar) |
| 18 | Pacific north-east of Hiva Oa, Marquesas | 2023-11-11 | ocean | Partial | no |
| 19 | Porto Murtinho, Mato Grosso do Sul, Brazil | 2021-12-07 | land | Match | no |

## Stations

### 0. Champigny-sur-Marne, Val-de-Marne, France
48.818, 2.520 · steps 0–0 · tile 2017-03-27 · from start · 5,070 km to next

Champigny-sur-Marne hosted a 2017 Grand Paris Express Line 15 South structure, [OA 813](https://www.ffgb.be/fr/projects/grand-paris-express-oa-813), the entry point for the first tunnel boring machine. The Société du Grand Paris [commissioned satellite radar monitoring of ground displacement in 2015](https://www.geoconnexion.com/news/grand-paris-express-first-results-of-satellite-monitoring), with [monthly reports once works began](https://www.batiweb.com/actualites/collectivites-territoriales/les-travaux-du-grand-paris-express-seront-surveilles-par-satellites-26867), though no source confirms what was measured here in March 2017.

### 1. Kivalliq Region, Nunavut, Canada
64.623, -83.939 · steps 1–24 · tile 2023-08-07 (range 2019-08-13 to 2023-08-07) · 5,070 km from previous · 7,931 km to next

No conclusive information found.

### 2. Jutaí, Amazonas, Brazil
-5.793, -69.255 · steps 25–34 · tile 2020-08-02 (range 2019-05-10 to 2022-07-28) · 7,931 km from previous · 18,050 km to next

[Greenpeace](https://www.greenpeace.org/aotearoa/press-release/new-images-of-illegal-fires-in-the-amazon-show-destruction-advances/) cited INPE's count of 29,308 fire hotspots in August 2020 and reported a record 8,031 for Amazonas state. Its overflights that month targeted DETER and PRODES satellite alerts in Amazonas and three other states, but Jutaí is not named.

### 3. Northern South China Sea
21.691, 118.535 · steps 35–45 · tile 2022-08-26 (range 2019-02-03 to 2023-04-28) · 18,050 km from previous · 16,110 km to next

[Typhoon Ma-on](https://www.hko.gov.hk/en/publica/tc/tc2022/section3_4rpt.html) entered the northern South China Sea on the night of 23 August 2022 and made landfall near Maoming before noon on 25 August, the day before this tile. No source places the storm at this tile or ties the image to a decision.

### 4. Southern Ocean near Cape Horn
-56.183, -69.721 · step 46 · tile 2023-01-06 · 16,110 km from previous · 8,403 km to next

No conclusive information found.

### 5. Tropical North Atlantic
17.470, -49.660 · steps 47–55 · tile 2022-10-08 (range 2020-02-01 to 2023-05-01) · 8,403 km from previous · 5,096 km to next

No conclusive information found.

### 6. South Atlantic near Ascension Island
-9.835, -12.402 · steps 56–67 · tile 2023-05-30 (range 2021-01-20 to 2023-05-30) · 5,096 km from previous · 12,906 km to next

[Oxford researchers](https://www.oxfordmartin.ox.ac.uk/news/marine-protected-areas-success) trialled satellite monitoring of illegal fishing in Ascension's protected waters from January 2014 to March 2017, and the island's [2020–21 compliance strategy](https://www.ascensionmpa.ac/resources/Ascension-Fisheries-Compliance-Strategy-v-10.pdf) makes AIS monitoring, plus satellite imagery when intelligence calls for it, part of baseline surveillance. The station lies about 307 km from Georgetown (my estimate), inside a 200-nautical-mile zone, but no source covers May 2023.

### 7. Unorganized Borough, Alaska, USA
64.085, -144.509 · steps 68–75 · tile 2020-04-11 (range 2019-02-01 to 2023-02-05) · 12,906 km from previous · 5,212 km to next

No conclusive information found.

### 8. Tallapoosa County, Alabama, USA
33.054, -85.798 · steps 76–81 · tile 2019-04-10 (range 2019-04-10 to 2023-04-19) · 5,212 km from previous · 7,537 km to next

No conclusive information found.

### 9. Méridja, Béchar Province, Algeria
31.482, -3.421 · steps 82–92 · tile 2016-03-02 (range 2016-03-02 to 2023-09-22) · 7,537 km from previous · 8,680 km to next

Méridja lies [about 15 km west of the Djorf Torba dam](https://en.wikipedia.org/wiki/M%C3%A9ridja) on the Oued Guir, and a [study presented in December 2016](https://dspace.univ-ouargla.dz/jspui/handle/123456789/14178) assessed water resources in the Méridja region. No source I could read links a satellite image to this place in 2016.

### 10. Bay of Bengal off Andhra Pradesh, India
16.392, 82.180 · steps 93–129 · tile 2021-05-30 (range 2019-02-15 to 2023-10-12) · 8,680 km from previous · 1,686 km to next

[Argus reported on 26 April 2021](https://www.argusmedia.com/en/news-and-insights/latest-market-news/2208905-bp-reliance-add-to-offshore-india-gas-production) that BP and Reliance had started production from the Satellite Cluster ("Satellite" is the field's name, not a spacecraft) in the Krishna Godavari basin off India's east coast, about a month before this tile. No source places the field in this tile or reports satellite imagery being used here.

### 11. Zhegu Township, Tsomei County, Shannan, Tibet, China
28.788, 91.687 · steps 130–310 · tile 2022-12-12 (range 2019-01-17 to 2023-12-02) · 1,686 km from previous · 5,117 km to next

Zhegu township hosts the Zhegu wind farm, described as the world's highest at 5,000–5,200 m, which [connected its first 10 turbines in December 2021](https://www.ithome.com/0/594/164.htm) and [completed Phase II in October 2023](https://www.ithome.com/0/723/058.htm). The tile falls between the two phases, and no source reports satellite imagery being used for the project.

### 12. Khafsa Subdistrict, Aleppo Governorate, Syria
35.794, 37.903 · steps 311–327 · tile 2023-01-27 (range 2017-09-25 to 2023-02-26) · 5,117 km from previous · 10,853 km to next

The station falls in Khafsa subdistrict, and in March 2016 the [UN described the al-Khafseh facility](https://news.un.org/en/node/523712) as the sole source of drinking water for Aleppo city and the eastern governorate, drawing from the Euphrates. That is seven years before this tile, and no source covers January 2023 or any satellite use.

### 13. Inland Western Australia
-19.446, 123.035 · steps 328–332 · tile 2020-04-25 (range 2020-04-25 to 2023-04-20) · 10,853 km from previous · 10,677 km to next

No conclusive information found.

### 14. Chernoyarsky District, Astrakhan Oblast, Russia
47.919, 46.050 · steps 333–352 · tile 2020-09-01 (range 2019-07-06 to 2023-10-01) · 10,677 km from previous · 6,355 km to next

No conclusive information found.

### 15. Dongfang, Hainan, China
19.178, 108.627 · steps 353–409 · tile 2022-03-26 (range 2018-08-19 to 2023-11-01) · 6,355 km from previous · 12,633 km to next

[China Energy News reported on 7 March 2022](https://paper.people.com.cn/zgnybwap/html/2022-03/07/content_25906620.htm), 19 days before this tile, that Hainan had named the waters west of Dongfang among 11 priority offshore wind sites totalling about 12.3 GW. No source reports satellite imagery being used for this planning.

### 16. El Mina, Nouakchott, Mauritania
18.010, -16.003 · steps 410–425 · tile 2018-12-09 (range 2018-12-09 to 2022-04-22) · 12,633 km from previous · 7,513 km to next

[The New Arab reported in April 2015](https://www.newarab.com/news/mauritanian-capital-risk-rising-sea-levels) that satellite imagery showed flood risk rising in parts of Nouakchott, tied to eroded sandbanks and a city site 50 cm below sea level. That is more than three years before this tile, and no source I could read covers December 2018.

### 17. Antofagasta de la Sierra, Catamarca, Argentina
-26.631, -68.004 · steps 426–481 · tile 2021-11-24 (range 2016-03-05 to 2023-09-15) · 7,513 km from previous · 7,562 km to next

[Pereira et al. (2024)](https://revistas.unlp.edu.ar/geoacta/article/download/17083/18656/85268) report that radar imagery and GPS measured the Cerro Blanco caldera sinking by about 0.7 cm a year in 2014–2020, down from 2.6 cm a year in 1992, and that a new GNSS and gravity survey followed in 2021, the tile's year. The caldera is roughly 30 km from the station (my estimate), so this documents the neighbourhood, not this image.

### 18. Pacific north-east of Hiva Oa, Marquesas, French Polynesia
-8.577, -138.078 · steps 482–487 · tile 2023-11-11 (range 2019-07-20 to 2023-11-11) · 7,562 km from previous · 8,754 km to next

The [Tainui Atea managed marine area](https://www.service-public.pf/diren/2024/11/28/tainui-atea-le-plan-de-gestion-2023-2037-de-laire-marine-geree/) covers French Polynesia's whole EEZ under a 15-year plan for 2023–2037, and the station lies about 165 km from Hiva Oa (my estimate), inside the 200-nautical-mile limit. The page does not mention surveillance, and no source covers satellite use here in November 2023.

### 19. Porto Murtinho, Mato Grosso do Sul, Brazil
-20.254, -57.157 · steps 488–494 · tile 2021-12-07 (range 2019-01-22 to 2022-02-10) · 8,754 km from previous · 9,223 km to next

[Mato Grosso do Sul's environment agency reported on 16 September 2021](https://www.imasul.ms.gov.br/?p=91319) that the Paraguay River gauge at Porto Murtinho read 115 cm, 51 cm below the same day in 2020, in what it called a critical drought. The station is in the municipality, roughly 180 km north of the town (my estimate), and no source covers December 2021 or satellite use.

## What the test showed about the spec

1. **A station has no single date.** Each cell keeps its earliest product, so one station can mix tiles years apart: stations 9 and 17 both span 2016 to 2023. I used the tile nearest the median, which makes that one tile stand in for the whole station. The spec should say which date counts, or research should run per tile for long stations.
2. **The operational question is rarely answerable from public sources.** Sources describe what was happening at a place, and only sometimes how satellites were used there. None mentions the specific image. "Pertaining to operationality" needs a threshold: is a wind farm under construction enough, or must a source show imagery in use?
3. **Sources often describe other sensors.** Stations 0 and 17 rest on radar and station 6 largely on AIS, while the agent sees Sentinel-2 optical tiles. A narrator could wrongly imply the agent's image was the one used.
4. **Ocean stations never reached a Match.** The 6 ocean stations came back 4 Partial and 2 None, against 6 Match, 3 Partial and 5 None for the 14 land and coast stations. Ocean stations may need a different kind of research, because a place name is what makes a search work and open water has none.
5. **Two sentences is tight when the caveat matters.** Most second sentences here go on saying what the source doesn't show. A separate evidence field, like the grades above, would leave both sentences for content.
6. **"Station" doesn't cover the start.** Station 0 is one step before the first long jump, so it wasn't teleported to. I kept it.

## Unverified leads

These surfaced in search summaries, but the pages couldn't be read, so they aren't used above. They are the first things to retry by hand.

- **Station 19:** a [Brazilian geological survey report](https://rigeo.cprm.gov.br/bitstream/doc/22535/3/relatorio_SAH_paraguai_2021%20.pdf) reportedly gives the 2021 Paraguay River level at Porto Murtinho as the second lowest on record (TLS certificate error).
- **Station 9:** a [Medias24 fact-check](https://medias24.com/2025/02/01/fact-checking-non-les-barrages-marocains-ne-menacent-pas-la-securite-hydrique-algerienne/) reportedly uses satellite image history to dispute Algerian claims that Moroccan dams dried out Djorf Torba (HTTP 403). It comes from one side of a contested dispute and dates from 2025.
- **Station 16:** a [remote-sensing study of the Nouakchott coast](https://hal.archives-ouvertes.fr/hal-00014206) reportedly uses SPOT imagery to track change since the Port de l'Amitié was built (blocked by bot protection).
