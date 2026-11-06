# CROPS template v1 — review copy

Standard: **SAOSO v2.1 (2026)** · source: `pgs_docs/6. PGS Farm visit assessment form - Crops, Animals, Seeds, agro-processing, summary_2026.xlsx, sheet 6.B.1.Crops (D28: hand-authored, not extracted)` · declared gaps: V15, V31

Generated from `core/templates_data/crops.v1.json` by `scripts/crops_template_review.py`. **Read it against FORM `6.B.1.Crops`**: one row here per printed line, in the sheet's order. The polarity column is the assessor's meaning of the answer (which answer is compliant), not a score.

## PART A — General information

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 1.1 | List the crops you are currently producing, as well as any others you are planning to produce in the forthcoming season: | TEXTAREA | FARMER |  |
| 2.1 | Total hectares cultivated | NUMBER | FARMER |  |
| 2.2 | Total hectares pasture | NUMBER | FARMER |  |
| 2.3 | Total hectares of farm (total surface area (hectares) of farm) | NUMBER | FARMER |  |
| 3.1 | How long has the land been farmed organically? | TEXT | FARMER |  |
| 3.2 | Describe the history of land use, any activities that took place previously and over what period. | TEXTAREA | FARMER |  |

## PART B — Crop production · Section 1: Fertility management

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 4.1 | Describe your soil fertility plan. How do you maintain and increase the health of your soil, manage fertility, recycle nutrients and build microbial life and living soils? Please list all products you add to your soil or foliage. | TEXTAREA | FARMER |  |
| 4.2 | Do you make your own compost? | YES_NO | FARMER | **self-check** |
| 4.3 | List your compost ingredients, their sources, as well as supplier details. (use 6.B.2 List input suppliers) | TEXTAREA | FARMER | links to INPUT_REGISTER |
| 4.4 | If you use animal manure, please describe the source. | TEXTAREA | FARMER |  |
| 4.5 | Describe your composting process, routine and quantities produced. | TEXTAREA | FARMER |  |
| 5.1 | Do you purchase compost? | YES_NO | FARMER | **self-check** |
| 5.2 | List your supplier/s | TEXTAREA | FARMER | attach: Compost supplier letter listing ingredients, sources, additives and process |
| 6.1 | Do you use mulching? | YES_NO | FARMER |  |
| 6.2 | If yes, what materials are you using and where are they sourced? | TEXTAREA | FARMER |  |
| 7.1 | Do you practice crop rotation? | YES_NO | FARMER |  |
| 7.2 | Please explain your process. | TEXTAREA | FARMER |  |
| 8.1 | Do you plant cover crops and "green manure"? | YES_NO | FARMER |  |
| 8.2 | Please describe routines for green manure and types of cover crops grown. | TEXTAREA | FARMER |  |
| 9.1 | Do you cover your crops with netting, sheeting or frost covers? | YES_NO | FARMER |  |
| 9.2 | If yes, how do you dispose of old/used netting or sheets? | TEXTAREA | FARMER |  |
| 10.1 | What type of soil do you have? | TEXT | FARMER |  |
| 10.2 | Have you ever had your soil tested? If yes list the service provider. | TEXTAREA | FARMER |  |
| 10.3 | Describe and attach a copy of the results (if applicable) | TEXTAREA | FARMER | attach: Soil test results (including Soil Organic Matter and Cation Exchange Capacity where the lab reports them) |

## PART B — Crop production · Section 2: Plant management

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 11.1 | Do you purchase seeds? If so, are they organic, conventional untreated or conventional treated? (please list suppliers) Important: the status of each seed needs to be recorded — this is baseline information against which future improvements in the proportion of organic seeds used by the farmer can be assessed | TEXTAREA | FARMER | **self-check** |
| 11.2 | Are all your seeds non-GMO? (If from conventional sources, please request a letter from the seed suppliers stating that the seeds are not treated, and not GMO and attach to the assessment) | YES_NO | FARMER | attach: Seed supplier letter stating the seed is not treated and not GMO; **self-check** |
| 11.3 | If conventional seeds are used, please explain why organic seeds are not used. Please describe your plan for securing a supply of organically grown seeds in the future. This plan must include a time line. | TEXTAREA | FARMER |  |
| 11.4 | Do you grow your own seedlings? Please list all ingredients in your soil mix and sources. | TEXTAREA | FARMER |  |
| 11.5 | Do you purchase seedlings? If yes, please list suppliers. (If from conventional sources, request letter from supplier stating source of seed, non-GMO status, ingredients in soil mix and any liquid feeds and attach to the assessment) | TEXTAREA | FARMER | attach: Seedling supplier letter: seed source, non-GMO status, soil-mix ingredients and liquid feeds |
| 12.1 | Do you harvest your own seeds? | YES_NO | FARMER |  |
| 12.2 | Describe your process. | TEXTAREA | FARMER |  |
| 13.1 | Do you plant different varieties of the same crop? | YES_NO | FARMER |  |
| 13.2 | Provide details on the varieties of the same crops that you grow. | TEXTAREA | FARMER |  |
| 13.3 | Have you noticed specific varieties that are well suited to your environment? | TEXTAREA | FARMER |  |
| 14.1 | Are you part of a seed bank/exchange initiative? | YES_NO | FARMER |  |
| 14.2 | Describe how often you meet, your role in the seed exchange, the portion of your seeds you get from the exchange | TEXTAREA | FARMER |  |

## PART B — Crop production · Section 3: Water management

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 15.1 | What is your water source? | TEXTAREA | FARMER |  |
| 16.1 | Has your water been tested? | YES_NO | FARMER |  |
| 16.2 | Please give details and attach results of most recent water test. (if applicable) | TEXTAREA | FARMER | attach: Most recent water test results |
| 16.3 | How are water sources protected from possible contamination? | TEXTAREA | FARMER |  |
| 17.1 | Describe your irrigation system/methods. | TEXTAREA | FARMER |  |
| 18.1 | Do you have an irrigation schedule? | YES_NO | FARMER |  |
| 18.2 | Explain your schedule | TEXTAREA | FARMER |  |
| 19.1 | Do you harvest rainwater/runoff? | YES_NO | FARMER |  |
| 19.2 | Explain your schedule | TEXTAREA | FARMER |  |
| 19.3 | What measures are in place or planned for preventing/minimising erosion and loss of topsoil? | TEXTAREA | FARMER |  |

## PART B — Crop production · Section 4: Environmental management

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 20.1 | How do you make more land available for cultivation? | TEXTAREA | FARMER |  |
| 20.2 | Are there plans for expansion of production areas? Please indicate on the farm map noting existing vegetation or land use. | TEXTAREA | FARMER |  |
| 21.1 | Are there any wetlands or indigenous wildlife areas on your property? | YES_NO | FARMER |  |
| 21.2 | If yes, describe how you manage/monitor them. | TEXTAREA | FARMER |  |
| 21.3 | What part of your farm is committed to farm biodiversity and do you have plans to expand? | TEXTAREA | FARMER |  |
| 22.1 | Are you aware of any endangered species on your property and/or vicinity? Give a short description, and explain your strategies in dealing with these species. | TEXTAREA | FARMER |  |

## PART B — Crop production · Section 5: Pest and disease management

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 23.1 | Do you have problems with pests? | YES_NO | FARMER |  |
| 24.1 | Please describe your plan to prevent and manage pests and disease on your farm. Explain also any methods/self-made preparations used to control pests on your crops. | TEXTAREA | FARMER |  |
| 25.1 | List any preparations you purchase and the suppliers. | TEXTAREA | FARMER |  |
| 26.1 | Do you have any problems with crop diseases? | YES_NO | FARMER |  |
| 26.2 | Explain any methods used to control such diseases. | TEXTAREA | FARMER |  |
| 27.1 | List any preparations and suppliers of disease control products. | TEXTAREA | FARMER |  |
| 27.2 | Describe application methods, quantity and frequency. | TEXTAREA | FARMER |  |
| 27.3 | Do you have challenges with weeds? What is your approach in reducing population and control of weeds. | TEXTAREA | FARMER |  |

## PART B — Crop production · Section 6: Pollution and contaminants

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 28.1 | Are there any conventional farms bordering your property? | YES_NO | FARMER |  |
| 28.2 | If so, explain how you deal with the risk of spray drift, ground water run-off or chemical contamination. | TEXTAREA | FARMER |  |
| 29.1 | Are there any non-farming (e.g. industrial/manufacturing) activities or major roads on or near your farm? | YES_NO | FARMER |  |
| 29.2 | If so, explain how you deal with any pollutants. | TEXTAREA | FARMER |  |
| 29.3 | Please describe the activities of adjoining land to your property. | TEXTAREA | FARMER |  |
| 30.1 | Where and how do you store solvents, paints, fuel and domestic chemicals? | TEXTAREA | FARMER |  |
| 30.2 | Is farm equipment checked and maintained regularly to prevent oil and fuel leaks? | YES_NO | FARMER |  |
| 31.1 | Is your farming equipment used for any non-organic agriculture or non-farming activity? | YES_NO | FARMER |  |
| 31.2 | If so, explain your cleaning/decontamination routine. | TEXTAREA | FARMER |  |

## PART C — Harvesting, collecting, handling, packing and transport · Section 7: Harvesting, packing and transport

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 32.1 | Describe your harvesting/collection and bulk packing process. | TEXTAREA | FARMER |  |
| 33.1 | What do you use to pack and package your crops/products for sale/retail? | TEXTAREA | FARMER |  |
| 33.2 | List sources and suppliers. | TEXTAREA | FARMER |  |
| 33.3 | What information is provided on the packaging? (if applicable) | TEXTAREA | FARMER |  |
| 34.1 | How are your products transported to market? | TEXTAREA | FARMER |  |

## PART C — Harvesting, collecting, handling, packing and transport · Section 8: Cleaning, disinfecting and sanitation

| Ref | Question (as the template stores it) | Type | By | Also |
|---|---|---|---|---|
| 35.1 | List the cleaning and disinfecting products you are currently using. | TEXTAREA | FARMER |  |
| 35.2 | What are your separation measures? | TEXTAREA | FARMER |  |
| 36.1 | Where do you sort, wash, and pack your products? | TEXTAREA | FARMER |  |
| 37.1 | Describe the cleaning and sanitation procedures on your farm. | TEXTAREA | FARMER |  |
| 38.1 | Give a short description of your washing up/toilet facilities for workers/food handlers. | TEXTAREA | FARMER |  |

## Verdicts

| Verdict | Judges | The assessor's question | Polarity | Options |
|---|---|---|---|---|
| V01 (`crops.V01`) | Q1 | Are you satisfied that the farmer is/can produce the listed crops? | POSITIVE | YES/NO/NA |
| V02 (`crops.V02`) | Q2 | Is the information correct? | POSITIVE | YES/NO/NA |
| V03 (`crops.V03`) | Q3 | Is there need for a transition period? | INFORMATIONAL | YES/NO/NA |
| V04 (`crops.V04`) | Q4 | Is there adequate on-farm composting (on-farm composting is a key requirement of organic principles)? | POSITIVE | YES/NO/NA |
| ↳ `crops.V04.a` | — | Is the compost of a good quality? (decomposed, friable, organisms/biological life visible, etc.) | POSITIVE | YES/NO/NA |
| ↳ `crops.V04.b` | — | Is the source of all ingredients, including manure, acceptable? | POSITIVE | YES/NO/NA |
| V05 (`crops.V05`) | Q5 | Is the purchased compost acceptable? (source, materials, quality) | POSITIVE | YES/NO/NA |
| | | *Recommendation: a letter from the compost supplier, listing all ingredients and their sources, any additives and the process by which the compost is made.* | | |
| V06 (`crops.V06`) | Q6 | Are the mulching materials acceptable? | POSITIVE | YES/NO/NA |
| ↳ `crops.V06.a` | — | If raw materials are brought in/purchased, did the farmer describe a plan to work towards producing what is needed on site to support the fertility plan on the farm? | POSITIVE | YES/NO/NA |
| V07 (`crops.V07`) | Q7 | Did the farmer describe what crops were planted before the visit and what plants are planned after the crop? | POSITIVE | YES/NO/NA |
| V08 (`crops.V08`) | Q8 | Did the farmer describe the type of crops used for green manuring/cover crops? | POSITIVE | YES/NO/NA |
| V09 (`crops.V09`) | Q9 | Are they reused or recycled? | POSITIVE | YES/NO/NA |
| V10 (`crops.V10`) | Q10 | Are you satisfied with the soil or soil test? | POSITIVE | YES/NO/NA |
| ↳ `crops.V10.a` | — | Is there a need for any/further tests? | INFORMATIONAL | YES/NO/NA |
| V11 (`crops.V11`) | Q11 | Has the farmer described a plan for securing a supply of organically grown seeds and seedlings? (if applicable) | POSITIVE | YES/NO/NA |
| ↳ `crops.V11.a` | — | Is supplier information available? | POSITIVE | YES/NO/NA |
| V12 (`crops.V12`) | Q12 | Does the farmer have an understanding of seed propagation? | POSITIVE | YES/NO/NA |
| V13 (`crops.V13`) | Q13 | Is there evidence of varieties? | POSITIVE | YES/NO/NA |
| V14 (`crops.V14`) | Q14 | Is the exchange initiative organised/effective and is the farmer getting an adequate proportion of seeds from it? | POSITIVE | YES/NO/NA |
| V16 (`crops.V16`) | Q16 | Are there any risks of contamination of the water source? (septic tanks, effluent, etc.) | NEGATIVE | YES/NO/NA |
| V17 (`crops.V17`) | Q17 | Is the system applicable to the crop/soil/environment? (flood, micro jet, drip irrigation) | POSITIVE | YES/NO/NA |
| V18 (`crops.V18`) | Q18 | Is the schedule mindful of conservation and evaporation? | POSITIVE | YES/NO/NA |
| V19 (`crops.V19`) | Q19 | Any indication of swale use, contouring, minimal tillage, mulch/plant cover etc.? | POSITIVE | YES/NO/NA |
| ↳ `crops.V19.a` | — | Is there any evidence of erosion on property? | NEGATIVE | YES/NO/NA |
| ↳ `crops.V19.b` | — | Are there practices/plans in place to conserve and manage water on property and in crop production? | POSITIVE | YES/NO/NA |
| V20 (`crops.V20`) | Q20 | Is the process in line with organic/environmental principles? (Burning, virgin forest, etc.) | POSITIVE | YES/NO/NA |
| V21 (`crops.V21`) | Q21 | If there are indigenous/protected forests/wetlands does the farmer have a management strategy? | POSITIVE | YES/NO/NA |
| ↳ `crops.V21.a` | — | What percentage of the farm is dedicated to biodiversity? | POSITIVE | YES/NO/NA |
| V22 (`crops.V22`) | Q22 | Do you see evidence of faunal and floral diversity? | POSITIVE | YES/NO/NA |
| V23 (`crops.V23`) | Q23 | Do you see evidence of pests or pest damage? (no evidence might be a signal of pesticide use) | NEGATIVE | YES/NO/NA |
| V24 (`crops.V24`) | Q24 | Are the methods and preparations compliant with the standard? | POSITIVE | YES/NO/NA |
| V25 (`crops.V25`) | Q25 | Are the purchased preparations acceptable? | POSITIVE | YES/NO/NA |
| V26 (`crops.V26`) | Q26 | Are the methods of dealing with crop diseases acceptable? | POSITIVE | YES/NO/NA |
| V27 (`crops.V27`) | Q27 | Are the methods and preparations acceptable? | POSITIVE | YES/NO/NA |
| V28 (`crops.V28`) | Q28 | Are the methods sufficient and is the farm protected? | POSITIVE | YES/NO/NA |
| V29 (`crops.V29`) | Q29 | Are containment methods acceptable? (if applicable) | POSITIVE | YES/NO/NA |
| V30 (`crops.V30`) | Q30 | Are the processes and storage areas acceptable? | POSITIVE | YES/NO/NA |
| V32 (`crops.V32a`) | Q31 | Are the separation methods acceptable? | POSITIVE | YES/NO/NA |
| V32 (`crops.V32b`) | Q32 | Is the harvesting and post harvesting process efficient, hygienic and offer protection from pests? | POSITIVE | YES/NO/NA |
| V33 (`crops.V33`) | Q33 | Does the packaging have minimal adverse impact on the product and on the environment? | POSITIVE | YES/NO/NA |
| V34 (`crops.V34`) | Q34 | Is the transport described acceptable? | POSITIVE | YES/NO/NA |
| V35 (`crops.V35`) | Q35 | Are the products acceptable? | POSITIVE | YES/NO/NA |
| ↳ `crops.V35.a` | — | Are you satisfied that the farmer is compliant? | POSITIVE | YES/NO/NA |
| V36 (`crops.V36`) | Q36 | Is the area clean and organised? | POSITIVE | YES/NO/NA |
| V37 (`crops.V37`) | Q37 | Are the procedures acceptable? | POSITIVE | YES/NO/NA |
| V38 (`crops.V38`) | Q38 | Are the facilities acceptable? | POSITIVE | YES/NO/NA |

## Sheet I §2 records

| Key | FORM ref | What the visit asks to see |
|---|---|---|
| `crops.R01` | a | Farm sketch of layout of farm, buildings, production areas, wildlife habitats, access, neighbouring properties and activities |
| `crops.R02` | b | Sketches or diagrams of fields, indicating acreage and cultivation, pasture/range, stock densities |
| `crops.R03` | c | Farm diary recording main activities; planting, harvest quantities, applications, etc. |
| `crops.R04` | d | Records of purchases/donations of all inputs, including seeds/seedlings |
| `crops.R05` | e | Sales records |
| `crops.R06` | f | Input/output reconciliation report (this report compares two sets of data, like sales records and production records, to ensure accuracy and identify discrepancies) |
| `crops.R07` | soil_water | Soil test and water test results, including Soil Organic Matter and Cation Exchange Capacity |

## The self-check markers (D71)

| Derived from | Why it is asked at the front door |
|---|---|
| `crops.Q4.2` | The FORM’s verdict V4 describes adequate on-farm composting as "a key requirement of organic principles", so it is one of the first practices a visit looks at. |
| `crops.Q5.1` | Purchased compost is allowed, but its source and quality are checked (FORM V5) — the risk is what came in with it. The supplier list belongs in the application, not here. |
| `crops.Q11.1` | The standard prefers organically produced seed, allows in-conversion material, and then permits conventional seed provided it has not been treated with prohibited post-harvest pesticides (SAOSO 4.1.1). So "a mix" or "conventional untreated" does not disqualify you. What the visit needs later is the status of <em>each</em> seed lot, because the FORM uses that as the baseline for improvement — which is why one word is enough here and not enough then. |
| `crops.Q11.2` | The standard does not permit ingredients, additives or processing aids derived from GMOs (SAOSO 2.3.2), and the group can take samples for laboratory analysis (SAOSO 1.4.1). "Some are, some aren’t" is a common and answerable answer — it becomes a list of what to replace, not a refusal. |
| `crops.R01` | The visit needs to see the farm’s shape on one page — production areas, water, natural vegetation, and what is next door, because what neighbours do can affect what reaches your land (SAOSO 4.6, Avoiding contamination). A sketch is usually the fastest way to show it. |
| `crops.R02` | Field diagrams are how the visit checks that what you describe on paper matches what is planted — the record is compared against the land, not only read. |
| `crops.R03` | A diary is the evidence trail behind everything else you tell us: what was planted, what was harvested, what was applied. It is also what makes an input/output reconciliation possible at all. |
| `crops.R04` | Inputs are where a visit starts, because that is where an organic claim is easiest to lose: one treated seedling or one bag of conventional compost changes what the land has received. The evidence needed is <em>what</em> was bought and from where. <strong>The group does not ask what you paid</strong>, and it does not ask for your supplier contracts. |
| `crops.R05` | Sales records are how the visit shows that produce sold as yours was grown by you — the same traceability requirement that applies to bought-in produce (OPP §VI.3). The group does not ask what you earned, and the figure it looks for is the quantity, not the price. |
| `crops.R06` | This is the one comparison that proves the two halves agree: what you produced against what you sold. Where it does not exist, the group can help set one up — it is a record you build forward, and there is no requirement that you have been keeping it. |
| `crops.R07` | A soil test is a snapshot of soil health, not a pass mark, and neither the standard nor the assessment form sets a maximum age. A test from a few years ago is still a starting point — tell the visit when it was taken. A missing test is recorded, not held against you. |

