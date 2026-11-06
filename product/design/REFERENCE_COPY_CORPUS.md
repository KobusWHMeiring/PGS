# Reference copy corpus - SAOSO and PGS websites

**Fetched 2026-11-05** by `scripts/fetch_reference_copy.py`. Regenerate with that script;
`--refresh` re-fetches, otherwise it re-reads `_scratch/reference_html/`.

| | |
|---|---|
| pages | 32 of 32 |
| words | 13977 |
| pages carrying a forbidden claim | 1 |

## How to use this file

**Search it, do not read it.** It is a register sample, not an argument. When a sentence
in `COPY_DECK.md` needs rewriting and you want to know how a PGS body actually phrases
that thing, `rg` for the noun here - `visit`, `decision`, `member`, `committee`,
`assessment` - and read two or three lines around the hit. That is the whole method.

**It is not a source of truth for what this group may claim.** Three of these sites are
umbrella bodies or marketing surfaces, and they say things a single PGS group may not
repeat. The forbidden-claim column below is why: `pasture raised`, `GMO free`,
`biodynamic`, `chemical-free` and `spray-free` are producer statements, never PGS
endorsements, and `core/tests/test_claim_discipline.py` fails the build on all of them.
The sources of truth stay the OPP and the SAOSO standard, both in `pgs_docs/`.

**What it is genuinely good for**, in order: (1) the words for a procedure - these
bodies use `visit`, `committee`, `outcome`, `pledge`, and so should we; (2) sentence
length and paragraph length in an organisation that is not selling anything; (3) the
sound of a body admitting a hard thing, which is on the PGS SA self-critical pages.

**What it will pull you into if you are careless:** the tricolon, the abstract headline,
and the adjective. Several of these pages read as generated. Being *as good as* them is
not the bar; being plainer than them is.

## Three things this corpus shows, so you do not have to find them

1. **The assurance vocabulary differs, and ours is the stricter one.** The Western Cape
   group writes *"Verify which farmers have been certified by the Western Cape Farmers'
   PGS"*. This group may not: membership is not certification, and MVP 0 publishes no
   seal and no farm status. Read their pages for *procedure*, never for status words.
2. **The tells are not machine-only.** The sibling group's opening is a textbook
   tricolon - *"through trust, transparency, and peer-to-peer collaboration"* - and its
   best sentence is a negate-then-assert: *"Each farm is visited at least once a year -
   not only to uphold standards, but also to share knowledge and strengthen connections."*
   Written by a person. So the rule in `COPY_VOICE.md` is a budget, not a ban: one such
   move per page is a voice, four is a template.
3. **Where these bodies are plainest is in procedure.** The PGS SA session write-ups and
   the SAOSO conversion guidance use short declaratives and no adjectives, because they
   are describing what happens. That is the register to search for when a deck string is
   about a visit, a decision or a fee.

## Index

| source | page | words | claims |
|---|---|---|---|
| SAOSO | [SAOSO](https://www.saoso.org/) | 168 | - |
| SAOSO | [About Us - SAOSO](https://www.saoso.org/about-us/) | 416 | - |
| SAOSO | [What We Do - SAOSO](https://www.saoso.org/what-we-do/) | 1020 | biodynamic |
| SAOSO | [Organic Certification - SAOSO](https://www.saoso.org/organic-certification/) | 257 | - |
| SAOSO | [Choose Organic - SAOSO](https://www.saoso.org/choose-organic/) | 493 | - |
| SAOSO | [FAQ - SAOSO](https://www.saoso.org/faq/) | 1020 | - |
| SAOSO | [Membership - SAOSO](https://www.saoso.org/membership/) | 290 | - |
| SAOSO | [Why Organic - SAOSO](https://www.saoso.org/knowledge-hub/why-organic/) | 411 | - |
| SAOSO | [Farmer Hub - SAOSO](https://www.saoso.org/knowledge-hub/farmer-hub/) | 117 | - |
| SAOSO | [Converting to Organic - SAOSO](https://www.saoso.org/knowledge-hub/farmer-hub/converting-to-organic/) | 123 | - |
| SAOSO | [Contact - SAOSO](https://www.saoso.org/contact/) | 71 | - |
| PGS SA | [PGS SA - PGS](https://www.pgssa.org.za/) | 338 | - |
| PGS SA | [About Us - PGS](https://www.pgssa.org.za/about-us/) | 1600 | - |
| PGS SA | [What Is PGS? - PGS](https://www.pgssa.org.za/what-we-do/) | 327 | - |
| PGS SA | [Our Work - PGS](https://www.pgssa.org.za/our-work/) | 555 | - |
| PGS SA | [Organic Certification - PGS](https://www.pgssa.org.za/organic-certification/) | 615 | - |
| PGS SA | [Why Organic - PGS](https://www.pgssa.org.za/why-organic/) | 461 | - |
| PGS SA | [Pollinator Map - PGS](https://www.pgssa.org.za/find-organic-food/) | 38 | - |
| PGS SA | [Membership - PGS](https://www.pgssa.org.za/membership/) | 460 | - |
| PGS SA | [Resources - PGS](https://www.pgssa.org.za/resources/) | 1358 | - |
| PGS SA | [Training Page - PGS](https://www.pgssa.org.za/training-page/) | 96 | - |
| PGS SA | [The Market - PGS](https://www.pgssa.org.za/the-market/) | 66 | - |
| PGS SA | [5th Session : How PGS groups organise for market and integrity of production - PGS](https://www.pgssa.org.za/how-pgs-groups-organise-for-market-and-integrity-of-production/) | 380 | - |
| PGS SA | [3rd Session Making PGS Groups sustainable - PGS](https://www.pgssa.org.za/making-pgs-groups-sustainable/) | 361 | - |
| PGS SA | [1st Session :The challenge of honouring the fundamentals of PGS - PGS](https://www.pgssa.org.za/the-challenge-of-honouring-the-fundamentals-of-pgs/) | 358 | - |
| Cape PGS | [Western Cape Farmer's PGS – Western Cape Farmer's PGS](https://pgs.org.za/) | 695 | - |
| Cape PGS | [Our Farmers – Western Cape Farmer's PGS](https://pgs.org.za/farmers/) | 205 | - |
| Cape PGS | [Documentation – Western Cape Farmer's PGS](https://pgs.org.za/documentation/) | 63 | - |
| Cape PGS | [Resources – Western Cape Farmer's PGS](https://pgs.org.za/resources/) | 66 | - |
| Cape PGS | [Contact – Western Cape Farmer's PGS](https://pgs.org.za/contact/) | 70 | - |
| IFOAM | [Participatory Guarantee Systems | IFOAM](https://www.ifoam.bio/our-work/how/standards-certification/participatory-guarantee-systems) | 434 | - |
| IFOAM | [Participatory Guarantee Systems Toolkit | IFOAM](https://www.ifoam.bio/our-work/how/standards-certification/participatory-guarantee-systems/pgs-toolkit) | 1045 | - |

---

# SAOSO

## SAOSO

`https://www.saoso.org/` - SAOSO - fetched 2026-11-05 - 168 words

*Why this page is here:* home - the register the sector body opens with

Creating a united and strong Organic agroecological movement

Working towards food system transformation and enabling sustainable agriculture to flourish

Helping farmers transition to organic and farm sustainably.

Studies and ongoing trials from the global scientific community.

Transform the way you eat and purchase for a healthier world.

News and research towards a more connected and healthy food system.

Over the past few months, our organic community has continued to grow, connect and make progress, with new developments, ongoing…

We may have been a little quiet lately, but behind the scenes there’s been plenty happening. Over the past months,…

Part-time Admin & Logistics Support Officer

The SAOSO Foundation and Voluntary Association (VA) support the development of organic and agroecological farming systems in South Africa through…

Join South Africa’s Organic Agroecological Movement

Become a champion for sustainable food and farming

Make a recurring or one-time gift

Become a member and make a difference

Stay informed & Connected

Subscribe to our newsletter for the latest in organic and sustainable farming news.

## About Us - SAOSO

`https://www.saoso.org/about-us/` - SAOSO - fetched 2026-11-05 - 416 words

*Why this page is here:* who SAOSO is, and what it claims to do

The South African Organic Sector Organisation (SAOSO) is a non-profit organisation focused on uniting and growing the organic agriculture sector in South Africa.

Building resilient, eco-friendly, and biodiverse food systems for a sustainable South Africa.

To facilitate the transition to ecologically sound and sustainable systems of agriculture through training and skills development, research, programme development, maintaining standards in ecological practices, knowledge exchange, advocacy and policy development, growing awareness, as well as facilitating trade through market participation, and networking across South Africa.

Why SAOSO was Formed

In 2008, the NEDLAC Trade and Industries Chamber Fund for Research into Industrial Development Growth and Equity (FRIDGE) study was published.

This study developed a value chain strategy for sustainable development and the growth of organic agriculture and included the establishment of a body to represent the organic sector in the country. Subsequently in 2009, SAOSO was founded.

In 2023, the two voluntary associations SAOSO and Participatory Guarantee System South Africa (PGS SA) merged enabling operations to be streamlined.

PGS SA now functions as a division within SAOSO and continues to support the establishment of communities of practice and PGS groups that help facilitate local market access for organic and agroecological farmers.

A member of IFOAM Organics International, SAOSO is guided by the four principles of organic farming: health, fairness, ecology and care.

We recognise that food sovereignty begins with the right to seed, and respect for the soil and biodiversity. Our work is linked to the achievement of all the Sustainable Development Goals and the Seventh Generation Principle.

The Seventh Generation Principle is an Indigenous Knowledge concept that encourages us to think seven generations ahead – about 140 years into the future – and to decide whether our decisions today will benefit those children seven generations from now into our future.

The Rights of Mother Earth

The right to life, respect, and health free from contamination and genetic manipulation.

Rights of Indigenous Peoples

Prioritising justice, human dignity and the well-being of the indigenous communities.

Section 24 of the Constitution

Everyone is entitled to a healthy environment and it must be protected from harm.

A shared responsibility for well-being, creating a just, sustainable, and peaceful global society.

Organic sector working groups unite experts, farmers and stakeholders to collaborate on best practices, policy advocacy, market development, standards and training. These groups play a crucial role in promoting sustainable farming and tackling the unique challenges of organic and agroecological agriculture. Their collective efforts strengthen the growth, integrity and resilience of the organic sector.

## What We Do - SAOSO

`https://www.saoso.org/what-we-do/` - SAOSO - fetched 2026-11-05 - 1020 words

*Why this page is here:* the four or five things it lists as its work

> **Contains a phrase the build forbids: biodynamic.** The check is a plain substring search, so it may be a false positive - a member association's name, for instance. Find the sentence and judge it; do not copy it either way.

SAOSO takes responsibility for food sovereignty and sustainable development through organic production practices.

Organic agriculture has been proven to be more efficient in times of climate change and drought, and far better suited to the large majority of farmers who choose to farm in an ecologically sound manner.

Our strategy and work is focused on:

Harnessing opportunities for the organic sector

Research that furthers the adoption of organic agriculture

Access to market through PGS and organic certification

Collaborating and networking nationally, regionally and internationally

Uniting and promoting the organic agriculture sector

The emergent organic sector is defining our food heritage and best-practice land use. Support of local farmers assists South Africa’s economy to transform through a vibrant agricultural sector that will lead to social reform that will benefit all.

SAOSO’s mandate is to develop the organic sector from training programmes through to value chain activities. SAOSO has partnered with PGS SA to develop a grassroots movement of organic farmers nationally. Growing food sovereignty through partnerships and programs provincially. Aligning farmers to Ecological Organic Agriculture and PGS nationally, producing to the SAOSO standard.

SAOSO is the South African node of the Knowledge Hub for Organic Agriculture in Southern Africa (KHSA). KHSA aims to scale up the adoption of organic farming practices in the Southern African region and the South African-based Sustainability Institute provides support for project implementation in the region.

KHSA is part of the Knowledge Centre for Organic Agriculture in Africa (KCOA) project. The KCOA project is a collaborative country-led partnership funded by the German Federal Ministry of Economic Cooperation and Development (BMZ) and implemented by the Deutsche Gesellschaft für Internationale Zusammenarbeit (GIZ) GmbH and non-governmental organisations.

KHSA focuses on project activities in Zambia, led by Participatory Ecological Land Use Management (PELUM) Zambia; in Namibia, led by the Namibia Nature Foundation in collaboration with the Namibian Organic Association; and in South Africa, led by the South African Organic Sector Organisation (SAOSO). GIZ is also working on projects in north, east, west and central Africa.

Participatory Guarantee Systems South Africa (PGS SA) was established in 2011 and is the body representing PGS groups in the country. It is dedicated to supporting the establishment of provincial communities of practice and PGS groups that help facilitate local market access for organic and agroecological farmers.

To expand the awareness and uptake of organic farming methods, SAOSO and PGS SA trained and supported 20 PGS Pollinators or community practitioners to establish new PGS groups in South Africa.

In 2023, SAOSO and PGS SA merged enabling operations to be streamlined. PGS SA, now a division of SAOSO, plays a vital role in empowering smallholder farmer groups to unlock the economic, environmental and social benefits of organic farming. By fostering local, climate-resilient food systems, PGS SA helps maintain healthy soils and communities. Their transparent, farmer-focused model not only ensures the integrity of organic products for consumers but also creates a collaborative network for farmers through knowledge-sharing and farm visits. By driving food sovereignty and promoting farmer-led, community-based food systems, PGS SA strengthens regional value chains and fosters collaboration among stakeholders.

SAOSO and PGS SA are part of the technical working group tasked with harmonising the SANS:1369 Standard for Organic Production and Processing and the SAOSO Standard for Organic Production and Processing v1.7 to the latest version of the IFOAM norms and standards.

Version 2 of the SAOSO Standard has been released and accepted into the IFOAM standard and includes wild harvesting, beekeeping and honey production, aquaculture and insect production. This will also mean that the SABS Standard will be part of the international IFOAM Family of Standards of which SAOSO is already a member.

Promote and ensure transparency and integrity in the value chain, with producers aligned to the SAOSO Organic Standard for Production and Processing.

Promote and expand PGS across South Africa to support the development of alternative agricultural value chains.

Engage regional and international partners to preserve and regenerate healthy ecology and biodiversity through best agricultural practice.

Lobby and effect policy change to create an enabling environment for agroecology.

To maximise the benefits of organic agriculture to the environment, health and society.

Our most important partners in our quest to change the way our food is produced and to advocate for recognition of the many advantages of ecological organic agriculture are our members. We are here to represent you in the development of the organic value chain from farm to fork. We need to hear from you. Click on the button below to sign up or let us know how we can better represent you

Second on the list are those organisations that resonate with principles encompassed by The Rights of Mother Earth, The Earth Charter, Rights of Indigenous People and Section 24 of our Constitution. If you understand how the principles of organic agriculture – health, ecology, fairness and care – can lead to a more prosperous society where nutritious food is available for all, then we would like to partner with you.

SAOSO has partnered with the Participatory Guarantee System of South Africa (PGS SA) to develop a grassroots movement of organic farmers nationally. Growing food sovereignty through partnerships and programs provincially. Aligning farmers to Ecological Organic Agriculture and PGS nationally, producing to the SAOSO standard.

SAOSO is a member of the International Federation of Organic Agriculture Movements (IFOAM) which is the worldwide umbrella organisation for the organic agriculture movement. IFOAM assisted with the development of the SAOSO standard.

SAOSO has partnered with Control Union, the accredited certifying body who can provide organic certification services to the SAOSO standard.

SAOSO has signed an agreement with The Sustainability Institute as the South African node of the Knowledge Hub for Organic Agriculture in Southern Africa to deliver activities on the ground that align with the aims and objectives of the Knowledge Centre for Organic Agriculture in Southern Africa. We are hopeful that this project will extend through to 2025.

Access Agriculture is a non-profit organisation that promotes the transitions towards organic farming and agroecology across the global South.

The Biodynamic Agricultural Association Southern Africa (BDAASA) strives to strengthen and advance the practice of biodynamic agriculture.

## Organic Certification - SAOSO

`https://www.saoso.org/organic-certification/` - SAOSO - fetched 2026-11-05 - 257 words

*Why this page is here:* how the sector body explains assurance - the closest thing to our own page's job

The South African organic certification landscape

Organic certification offers assurance that consumers can trust.

A first party organic certification is a “self-claim” which is not verified by outside parties. It covers a direct relationship between a farmer and a consumer whereby you visit the farm or discuss with the farmer and are satisfied with his claims.

Second-party organic certification in South Africa is assured by a Participatory Guarantee System (PGS) and works withshort supply chains. PGS provides a locally focused quality assurance system that certifies producers based on active participation. PGS SA is a SAOSO partner.

Third party organic certification is required for long supply chains and export. The processes are certified annually by an accredited certifying body (ACB) to specific organic standards.

SAOSO has developed a local Standard for Organic Production and Processing which is included in the IFOAM Family of Standards. Chapters 1, 2 and 3 are applicable to all crop and animal production systems. Chapters 8, 9 and 10 are applicable to all systems, including processing. Appendix 9 deals specifically with PGS systems.

The SAOSO organic standard is verified locally. Consumers can recognise compliance with the standard represented by these two trademarked logos.

If you would like to consider being third party certified, please go through this infographic.

Questions for farmers thinking about third party organic certification.

If you suspect misrepresentation or if you want verification that a product is in fact organic, then please contact SAOSO through our contact form.

See FAQ about organic certification here.

Third party SAOSO certification by Control Union

## Choose Organic - SAOSO

`https://www.saoso.org/choose-organic/` - SAOSO - fetched 2026-11-05 - 493 words

*Why this page is here:* consumer-facing persuasion, for contrast

#ChooseOrganic – it’s good for you, it’s good for the planet

Organic goes beyond a label – it’s a commitment to health, sustainability and fairness. It protects soil, water and biodiversity while supporting local supply chains and food security in South Africa. Choosing organic means supporting farmers who prioritise the environment and ensures quality, transparency and care in the food we consume.

Download our digital toolkit free to use consisting of:

Our designs have left space for you to add your brand’s logo and take ownership of this #ChooseOrganic campaign.

Any media enquiries, please contact: charmaine@saoso.org

Organic is a lifestyle, a philosophy and a science. It is a way of living in the world that is in harmony with nature. Healthy soils, ecosystems and people, are supported by organic farming practices.

Organic agriculture has been proven to be more efficient in times of climate change and drought, and far better suited to the large majority farmers who choose to farm in an ecologically-sound manner.

Why should you buy organic?

Food that is farmed organically is:

More nutritious and tasty

Farmed in a way that reduces pollution and protects the soil and water

From a system that preserves ecosystems and biodiversity

Fostering social justice and fairness in the foodsystem

Organic food is better for your health!

Research has shown that food that is grown organically is better for our health.

Organic crops contain higher levels of important antioxidants, minerals, and vitamins such as Vitamin C, iron, magnesium, and phosphorus that are better for our bodies and our general immunity.

Organic food also minimises our exposure to pesticides and toxins. Children are especially vulnerable to pesticides and avoiding this in their diets is beneficial.

Organic farming is better for the environment.

Organic farming is a win-win for people, animals and the planet. It takes a Gaia holistic approach that works with Mother Nature to grow healthy, nutritious food while at the same time preserving earth’s natural ecosystems.

It offers a solution to some of our greatest problems: climate change, food insecurity and biodiversity loss.

Ways that organic farming positively impacts the environment:

Eliminates persistent and harmful pesticides from entering the environment

Builds healthy topsoil and prevents erosion

Supports water conservation and water health

Reduces carbon dioxide and helps slow climate change

Preserves natural habitats for wildlife

Supports animal health and welfare

It doesn’t cause algae blooms or nitrate leaching from runoff from petroleum-based fertilisers often used in conventional farming

Encourages biodiversity which protects humanity from future health threats.

Types of organic farming

There are many different terms used for farming methods that fall under the umbrella of organic agriculture. See our explanations here.

Organic farmers use best practices to produce healthy food without the use of synthetic and chemical inputs. Learn about land design, water management, soil health, companion planting, holistic livestock management and permitted inputs.

Local and global research

Data and research supporting organic agriculture versus conventional towards sustainable food systems and food sovereignty.

## FAQ - SAOSO

`https://www.saoso.org/faq/` - SAOSO - fetched 2026-11-05 - 1020 words

*Why this page is here:* question-and-answer register

We answer the most commonly asked questions about organics in South Africa. We also have dedicated sections for farmer support, research data and consumer information.

General Enquiries about SAOSO

Organic Policy & Regulations

What is organic agriculture?

Organic agriculture is a production system that sustains the health of soils, ecosystems and people. It relies on ecological processes, biodiversity and cycles adapted to local conditions, rather than the use of inputs with adverse effects. It combines tradition, innovation and science to benefit the shared environment, promote fair relationships and a good quality of life for all.

Agroecology is an integrated approach that simultaneously applies ecological and social concepts and principles to the design and management of food and agricultural systems. It seeks to optimise the interactions between plants, animals, humans and the environment while taking into consideration the social aspects that need to be addressed for a sustainable and fair food system. Agroecology is a science, a practice and a social movement.

What is regenerative agriculture?

Regenerative Agriculture is a conservation and rehabilitation approach to food and farming systems. It focuses on topsoil regeneration, increasing biodiversity, improving the water cycle, enhancing ecosystem services, supporting bio-sequestration, increasing resilience to climate change, and strengthening the health and vitality of farm soil. It utilises a variety of sustainable agriculture techniques in combination.

What is organic in conversion or how do I convert to organic farming?

The establishment of a diverse and balanced farming system with a natural ability to regulate itself usually takes several years and involves mistakes and learning. Diversifying the farming system is a cornerstone to conversion and would include recycling valuable farm by-products. Farm animals are introduced into the system for both products and manures. Conversion will include the growing of cover crops and green manures. The SAOSO standards are used as a motivator and guide to production principles

What is conservation agriculture?

Conservation agriculture is a farming system that can prevent losses of arable land while regenerating degraded lands. It promotes maintenance of a permanent soil cover, minimum soil disturbance, and diversification of plant species.

What inputs are allowed in organic agriculture?

Please refer to the Section C – appendices of the SAOSO standard which details the criteria for the evaluation of inputs, additives and processing aids for organic production and processing.

Are genetically-modified organisms (GMO’s) allowed in organic agriculture?

Organic farmers and producers may not use ingredients, additives or processing aids derived from GMO’s. According to the SAOSO standard, inputs, processing aids and ingredients shall be traced back one step in the biological chain to the direct source organism from which they are produced to verify that they are not derived from GMOs.

How can I support SAOSO?

You can support our work by becoming a member or by making a donation.

How can I make a donation to SAOSO?

Go to our Donations page and easily gift a one-time or recurring amount through Payfast.

How do I become a member of SAOSO and what are the benefits?

Please go to our Membership page and join us to help drive the organic agriculture movement forward, creating a sustainable, healthier future for all. Benefits include our monthly email newsletter with updates on everything organic, voting rights at the annual SAOSO AGM giving you real power to transform our food system, access to our Organic Marketplace that links you to trade opportunities, and access to our Knowledge Products and research.

How do organisations work with SAOSO to increase the uptake of organic agroecological principles?

Our members and partners are actively transforming food and farming in South Africa. We work on the ground with farmers and PGS, drive research and training, inform media and consumers, and advocate for policy change. Together we can protect and regenerate soil, water, biodiversity and ecosystems, creating a landscape where wildlife, animals, people and planet thrive.

How do I access the SAOSO organic standards?

You can access the standard here.

How do I get organically certified?

Once your farm is ready to be third party certified, contact Hennie Louw at Control Union: hlouw@controlunion.com. If you are interested in second party organic certification for smallholder farmers, then please look at local PGS systems.

Can SAOSO certify me?

SAOSO is the custodian of the SAOSO Standard for Production and Processing and not an accredited certifying body.

What are the benefits of organic certification?

There are many. An organically certified farm improves water quality, increases biodiversity and contributes to soil health. It provides the consumer with chemical pesticide free produce that is better for their health. Being certified by a third party or by a PGS means that the retailer and customer can trust that what they are buying is genuinely organic.

Can I sell organic produce without certification?

Yes, but it cannot be labelled as organic. In South Africa, according to the Consumer Protection Act, farmers or producers can be held liable if they claim that their produce is organic but it is in fact not.

What is PGS certification?

PGS certification is second party assurance given by groups of farmers, consumers and retailers that the produce and processed are organic.

Does the South African government have regulations for organic agriculture?

Unfortunately, the Draft National Policy on Organic Agriculture (10th draft, circa 20??), has not been passed and neither has the Agroecology Strategy.

How can I be a part of advocating for policy change towards a more sustainable food system?

By becoming a member of SAOSO you can play an active part in transforming food and farming in South Africa towards a sustainable and healthier future.

Can I trust a product that is certified organic?

You can trust the SAOSO and PGS organic certification seals that you see on our certification landscape page. If you suspect misrepresentation or if you want verification that a product is in fact organic, then please contact SAOSO via info@saoso.org

Is my organic certification recognised overseas for export?

When exporting, products are certified to the standard of the country being exported to. However, through the IFOAM Family of Standards, there is a degree of equivalence to standards in that family for our local market.

## Membership - SAOSO

`https://www.saoso.org/membership/` - SAOSO - fetched 2026-11-05 - 290 words

*Why this page is here:* how a body asks people to join

Become a Member and SUPPORT THE Organic and Agroecology Movement

Joining SAOSO is more than just a membership – it’s a commitment to a healthier planet, nutrient-dense and safer food, and more sustainable farming practices.

By becoming part of SAOSO, you actively contribute to an agricultural evolution that focuses on building resilience, improving biodiversity, and ensuring food security through organic and agroecological practices.

Newsletter and Profiling: Stay informed with the SAOSO newsletter and get the chance to have your farming stories featured, increasing your profile in the community.

PGS Knowledge Products: Obtain access to a wealth of knowledge products related to PGS and organic farming, helping you stay informed and improve your techniques.

National Agroecology Producers WhatsApp Group: Join our channel for networking and sharing knowledge with your peers.

SAOSO Standard: Utilise the SAOSO standard, a benchmark for organic and agroecological farming in the region, ensuring best practices and quality in your farming operations.

Working Groups: Access information or be a part of working groups keeping you updated on key developments and initiatives.

PGS Webinars: Gain access to informative webinars offering valuable insights and learning opportunities.

SAOSO AGM: Voting rights at our annual AGM gives you real power to transform our food system.

Through joining SAOSO, you not only gain access to these exclusive benefits but also become part of a larger movement dedicated to promoting organic and agroecological farming practices that are sustainable, equitable and resilient.

Your membership is a step towards a healthier future for farming and food systems in South Africa.

For detailed membership benefits click here.

NGO’s, NPO’s & Co-ops

(Turnover less than R6 Million)

R 2,000.00 per Year.

(Turnover R6 – R50 Million)

R 5,000.00 per Year.

(Turnover over R50 Million)

R 10,000.00 per Year.

## Why Organic - SAOSO

`https://www.saoso.org/knowledge-hub/why-organic/` - SAOSO - fetched 2026-11-05 - 411 words

*Why this page is here:* the why-organic argument

SAOSO > Knowledge Hub > Why Organic

Organic is a lifestyle, a philosophy and a science. It is a way of living in the world that is in harmony with nature. Healthy soils, ecosystems and people, are supported by organic farming practices.

Organic agriculture has been proven to be more efficient in times of climate change and drought, and far better suited to the large majority farmers who choose to farm in an ecologically-sound manner.

Why should you buy organic?

Food that is farmed organically is:

More nutritious and tasty

Farmed in a way that reduces pollution and protects the soil and water

From a system that preserves ecosystems and biodiversity

Fostering social justice and fairness in the foodsystem

Organic food is better for your health!

Research has shown that food that is grown organically is better for our health.

Organic crops contain higher levels of important antioxidants, minerals, and vitamins such as Vitamin C, iron, magnesium, and phosphorus that are better for our bodies and our general immunity.

Organic food also minimises our exposure to pesticides and toxins. Children are especially vulnerable to pesticides and avoiding this in their diets is beneficial.

Organic farming is better for the environment.

Organic farming is a win-win for people, animals and the planet. It takes a Gaia holistic approach that works with Mother Nature to grow healthy, nutritious food while at the same time preserving earth’s natural ecosystems.

It offers a solution to some of our greatest problems: climate change, food insecurity and biodiversity loss.

Ways that organic farming positively impacts the environment:

Eliminates persistent and harmful pesticides from entering the environment

Builds healthy topsoil and prevents erosion

Supports water conservation and water health

Reduces carbon dioxide and helps slow climate change

Preserves natural habitats for wildlife

Supports animal health and welfare

It doesn’t cause algae blooms or nitrate leaching from runoff from petroleum-based fertilisers often used in conventional farming

Encourages biodiversity which protects humanity from future health threats.

Types of organic farming

There are many different terms used for farming methods that fall under the umbrella of organic agriculture. See our explanations here.

Organic farmers use best practices to produce healthy food without the use of synthetic and chemical inputs. Learn about land design, water management, soil health, companion planting, holistic livestock management and permitted inputs.

Local and global research

Data and research supporting organic agriculture versus conventional towards sustainable food systems and food sovereignty.

View Frequently Asked Questions about Organic Farming

## Farmer Hub - SAOSO

`https://www.saoso.org/knowledge-hub/farmer-hub/` - SAOSO - fetched 2026-11-05 - 117 words

*Why this page is here:* farmer-facing hub

SAOSO > Knowledge Hub > Farmer Hub

Technical support for smallholder and commercial farmers who are farming organically or want to transition to organic agriculture.

What makes a farm organic?

Organic farming works in harmony with nature. It focuses on healthy food, soils, plants, ecosystems and people as a priority. Organic farmers do not use synthetic fertilisers, pesticides, or GMOs, but instead utilise organic farming methods such as crop rotations, cover crops, organic inputs and holistic livestock management to provide clean, healthy food.

An organic farm is a working combination of tradition, innovation and science that benefits everyone sharing the environment, promoting a good quality of life for all.

For access to SAOSO’s organic standards, see here.

## Converting to Organic - SAOSO

`https://www.saoso.org/knowledge-hub/farmer-hub/converting-to-organic/` - SAOSO - fetched 2026-11-05 - 123 words

*Why this page is here:* conversion guidance - plain instruction, the OPP's own register

SAOSO > Knowledge Hub > Farmer Hub > Converting to Organic

There are two aspects that undergo conversion, one the practitioner him/herself and the other the approach, practices and processes to the work to be done. This impulse must always begin with the person.

Diversifying the farming system is a cornerstone to conversion and would include recycling valuable farm by-products. Farm animals are introduced into the system for both products and manures. Conversion will include the growing of cover crops and green manures. The SAOSO standards are used as a motivator and guide to production principles. The establishment of a diverse and balanced farming system with a natural ability to regulate itself usually takes several years and involves lots of mistakes and learning.

## Contact - SAOSO

`https://www.saoso.org/contact/` - SAOSO - fetched 2026-11-05 - 71 words

*Why this page is here:* how a body ends a page

Get in touch with us

Thank you for your interest in our work.

If you are interested in getting certified organic, please read our FAQ

If you are looking for farmer support, please see our Farmer Hub

Mon to Fri 8am – 5pm

By sharing your information with us, you are authorising SAOSO to retain your personal details. We retain and process your personal information in line with our Privacy Policy.


---

# PGS SA

## PGS SA - PGS

`https://www.pgssa.org.za/` - PGS SA - fetched 2026-11-05 - 338 words

*Why this page is here:* home

Harnessing the social, environmental and economic potential of organic farming

Local organic certification for farmers, retailers and consumers

- A foundation of trust

- And knowledge exchanges

Working towards a healthier and more robust food system

The Organic Farmer Journey

Farmer progression into the organic value chain through a community of practice and alignment with the organic certification road map.

Onboarding and nurturing a community of practice.

Farmer planning, set-up and practice.

Organisational mapping and support.

Establishment of the PGS

Adopting organic standards and finding markets.

Creating Localised Food Systems

Engaging with the certification road map, trade and opportunities

There are no upcoming events.

Read the latest stories about our organisation, our farmers and the best practices towards a healthier food system in South Africa

View Farm Visits Calendar

News from the Ground

Contribute towards the growth of PGS in South Africa

Be a part of the food sovereignty movement

Make A Recurring Or One-Time Gift

Join Us And Make A Difference

Sign Up For PGS News And Stories

Stay informed about our farms and farmers, latest insights and best practices.

Farmers on commonage or farming individual pieces of land traditionally or agroecologically/ poison-free, or farming conventionally with an intention to convert to organic production.

Farmers have taken the steps to organise themselves into an Organic Farmer Organisation with the focus on consolidating production to sell into local markets.

Production is consolidated and farmers now need support to access more production resources and markets. Through growing the community of practice, other stakeholders can participate in creating local food systems.

Farmers have surplus produce and have identified local markets that have interest in the development of local food systems. The PGS is established as a local quality assurance mechanism.

From here, the market drives production and the PGS groups are linked to local retailers and other stakeholders in the organic value chain and sell in the local markets and regional areas.

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## About Us - PGS

`https://www.pgssa.org.za/about-us/` - PGS SA - fetched 2026-11-05 - 1600 words

*Why this page is here:* who the national PGS body is

Established in 2011 as a voluntary association and then as a Non for Profit organisation in 2013, Participatory Guarantee Systems South Africa (PGS SA) is the body representing PGS groups in the country.

It is dedicated to supporting the establishment of provincial communities of practice and PGS groups that help facilitate local market access for organic and agroecological farmers.

IFOAM-Organics International, an international body promoting organic agriculture worldwide, recognised the need to support assurance systems suited to smallholder agriculture and local markets.

They articulated the basic elements and key features of existing smallholder farmer organisations worldwide that were working in a participatory way with consumers and local markets and classified these assurance systems as Participatory Guarantee Systems. “Participatory Guarantee Systems (PGS) are locally focused quality assurance systems.

They certify producers based on active participation of stakeholders and are built on a foundation of trust, social networks and knowledge exchange.” IFOAM – Organics International PGS SA assists smallholder farmer groups to harness the economic, environmental and social potential of organic farming in order to develop local food systems that are climate resilient and keep soils and people healthy.

This transparent, producer-focused system assures consumers of the integrity of organic products and links producers into a community of practice through knowledge exchanges, whilst developing consumer awareness around ethical choices that support local economic development.

PGS groups drive food sovereignty through localised, farmer-driven food systems based on community participation, transparency and trust.

They are key to galvanising local food systems and bringing collaboration between stakeholders in regional value chains.

PGS SA achieves this in the following ways: Training of smallholder farmers using organic and agroecology principles PGS SA promotes the development of organic farmer organisation (OFO) in collaboration with INOFO South Africa and the seeding of grassroots PGS groups through the PGS Pollinator and Co-pollinator Programmes.

Developing sustainable short value chains Creating knowledge resources for smallholder farmers’ adoption of PGS A member of IFOAM Organics International, PGS SA is guided by six elements Matthew is an entrepreneur, ecological designer, practitioner, and organic food systems advocate.

Butshabelo is passionate about agroecological practices that feed the nation with nutritious and healthy food.

Raymond has been farming organically in KwaZulu-Natal for 40 years and has had an active background in soils, trees, farmer training and agricultural research techniques.

Secretary and national PGS coordinator Sasha is a small-scale organic farmer and advocacy researcher, she is project manager for PGS SA and a PGS practitioner herself.

Administrative and Communications liaison Nthatise is zealous about indigenous organic agronomic practices, entrepreneur and is an agriculturalist Provincial PGS SA Representatives Reach out to the convenor of the working group you are keen to be part of to contribute to the SA organic sector SAOSO and PGS SA have developed to a point where many activities are already being carried out, and an appropriate structure needs to be established, incorporating planning capacity, ethical leadership and well-managed activities.

The Working Groups are operating as functions of SAOSO/PGS-SA, while some are related to specific projects and programmes.

What better way for organics to function than for it to be driven by its members.

Siyabonga has over 15 years’ experience in corporate and public sector marketing and communications.

Over the past four years, she has focused on alternative food systems working with small-scale farmers in Joburg and considers herself a food activist.

Market Development for PGS Create opportunities for PGS producers to link directly to local customers and earn fair prices for the fruits of their labour by selling direct.

Organic Value Chain Development Developing the organic value chain with vertical integration, scope for regional hubs and enhance public-private collaboration.

Raise awareness of PGS among governments, local authorities, development partners, SME’s and local NGO’s to encourage them to invest in PGS.

The establishment of the organic trade desk is the outcome of this working group.

EOA Farmer Support & Advisory Providing technical support to farmers from best practice organic methodology, organic growing innovations and traditional knowledge to land design, production, market access, training and monitoring the impact in the field of PGS and standards.

Strengthen capacities of stakeholder farmers to ensure the flow of information and use of new technologies, and organic best practice.

Supporting PGS groups and their farmer members by creating PGS friendly policies and enabling frameworks ensuring alignment to the SAOSO Standard for Organic Production and Processing and context specific for PGS groups.

The group focuses on the roll-out of the technology suite that is in development for the mapping and data collection process to inform the farmer support and market development working groups.

The aggregated data will assist in future fundraising and program development to connect provincial supply chains.

The technology is a central component to the role out of Organic 3.0 and digital value chains.

Create a PGS seed bank for accredited PGS farmers to draw from.

Special focus on indigenous seed; document seed catching mechanisms; treatments to improve seed and seedling health.

This group is focused on developing the provincial networks with the main goal to establish seed banks within PGS groups and wider agricultural networks.

Seed sovereignty is the main objective of this working group.

This group will be focused on furthering the research agenda for the organic sector.

Working closely with universities and other institutions such as ARC to bring organic into the mainstream.

This group will focus on fundraising activities for the future of PGS SA and SAOSO.

It will be working closely with steering committee members and all the WGs (and their specific fundraising requirements) to develop funding proposals and screening potential funders and linking the proposal to potential funding mechanisms.

Matters of governance for both PGSSA and SAOSO to ensure that their constitutions correctly serve the organisations.

The members of the PGS share a common goal and collectively embrace the principles of organic agriculture.

PGS rests on an “Integrity based approach” – trust and integrity form the basis of the system.

The group has a flat organisational structure which is developed and managed by peers.

The system is open to the public and peer scrutiny at all levels.

The members participate in the development and management of the process and procedures of the PGS which is “owned” and controlled by the collective.

The assessments and the process focus on skills and knowledge exchange.

PGS SA and SAOSO working with selected sector partners offer training courses to teach farmers about organic farming and take them through the Organic Farmer Journey to set them up as a PGS group.

Contact us to develop your customised training package.

PGS SA promotes the development of organic farmer organisation (OFO) in collaboration with INOFO South Africa and the seeding of grassroots PGS groups through the PGS Pollinator and Champion Programmes.

PGS SA is focused on growing the grassroots movement of agroecological producers to take ownership of our role in growing the economy of South Africa.

With climate change a growing concern, sourcing and producing local nutritious food in an ecological way is at the core of how we can adjust to a Post Covid world.

Rapid localisation and sustainable resource management is how we can adapt local food systems to suit the people’s needs.

PGS SA in collaboration with SAOSO and the organic sector working groups are developing knowledge resources to help farmers on the organic journey.

PGS SA promotes and supports the principles of organic agriculture as defined by the worldwide umbrella organisation for the organic agriculture movement, the International Federation of Organic Agriculture Movements (IFOAM).

IFOAM supports the development of PGS within the region and advocates for the recognition of PGS by governments.

To expand the awareness and uptake of organic farming methods, PGS SA in partnership with the South African Organic Sector Organisation (SAOSO) is training and supporting 20 Pollinators or community practitioners to establish new PGS groups in South Africa.

This programme is supported by the Knowledge Hub for Organic Agriculture in Southern Africa (KHSA).

The South African Organic Sector Organisation (SAOSO) is a non-profit organisation focused on growing the organic agriculture sector in South Africa.

Their work unites farmers, producers, retailers and consumers of organic products to collectively protect the future food freedom and natural ecology of South Africa, and their strategy is aligned with PGS SA.

The Knowledge Hub for Organic Agriculture in Southern Africa (KHSA) is part of the Knowledge Centre for Organic Agriculture in Africa (KCOA), a collaborative country-led partnership funded by the German Federal Ministry of Economic Cooperation and Development (BMZ) and implemented by the Deutsche Gesellschaft für Internationale Zusammenarbeit (GIZ) GmbH and non-governmental organisations across Africa.

The KCOA aims to scale up adoption of sustainable farming practices through five knowledge hubs in Africa.

The other hubs are implemented by GIZ with in-country partners in North, West, East and Central Africa.

The South African-based Sustainability Institute supports project implementation in Zambia, Namibia, Malawi and South Africa.

SAOSO and PGS SA lead on activities in South Africa.

Philippi Agrihub was launched in 2018 to support small-scale and emerging farmers by facilitating their access to value-add services and markets.

All their farmers receive training to grow organic produce and develop their business skills; PEDI is supplied by over a 100 farmers from the Cape Flats as well as its own farm.

The certification of farmers in the Cape Flats PGS on which PEDI forms part is ongoing.

Matthew is an entrepreneur, ecological designer, practitioner, and organic food systems advocate.

He is on the SAOSO Steering Committee, Chairman of PGS SA and is an IFOAM Ambassador, working broadly in the sector as a solutions architect and designer.

Matt is currently working as program

## What Is PGS? - PGS

`https://www.pgssa.org.za/what-we-do/` - PGS SA - fetched 2026-11-05 - 327 words

*Why this page is here:* its work, in its own words

PGS is a process of certifying organic products by ensuring that their production takes place in accordance with specific organic standards. In South Africa, local PGS groups certify according to the South African Organic Sector Organisation (SAOSO) standard.

The journey begins when a community of organic farmers has a surplus to sell and form a PGS in order to actively participate in the process of certifying one another’s farms. The group is built on a foundation of trust, transparency, participation, social networking and knowledge exchange.

PGS is a second-party organic assurance mechanism that serves as an alternative and complementary quality assurance system to third-party certification. Many PGS groups exist all over the world and some have been going for over 40 years. The worldwide umbrella organisation for the organic agriculture movement, the International Federation of Organic Agriculture Movements (IFOAM) supports the PGS community of practice and advocates for the recognition of PGS by governments.

Accessible and affordable for smallholder farmers.

Inclusive for consumers, retailers, distributors and processors who can all play a role in the process.

Designed as a short supply chain for nurturing local, organic produce into the market.

Fair and grounded in integrity, enabling farmers to get fair prices for their produce and for consumers to get food they can trust.

Our work is linked to the achievement of all the Sustainable Development Goals and the Seventh Generation Principle.

The Seventh Generation Principle is an Indigenous Knowledge concept that encourages us to think seven generations ahead – about 140 years into the future – and to decide whether our decisions today will benefit those children seven generations from now into our future.

PGS logos to look out for:

Look for the following logos when buying your organic food to get assurance that they are grown with organic and agroecological principles and practices.

See FAQ about PGS here.

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## Our Work - PGS

`https://www.pgssa.org.za/our-work/` - PGS SA - fetched 2026-11-05 - 555 words

*Why this page is here:* a second pass at the same subject - compare with /what-we-do/ for which version reads as written rather than generated

PGS groups have great potential to support organic agriculture and the localisation of South Africa’s food system. PGS assures traceability through on-going social interaction and acts as a vehicle for mutual learning and the development of complementary value chains. PGS is an essential component of South Africa’s Ecological Organic Agriculture (EOA) strategy.

PGS in South Africa by the numbers:

PGS groups in South Africa

Community of practice/ emerging PGS groups

HA under organic production

Our strategy and work is focused on:

Supporting a transparent, local organic certification system for farmers, retailers and consumers.

Creating a sustainable role for smallholder farmers in the organic sector.

Introducing smallholder organic farmers to the benefits of PGS.

Training of PGS pollinators and organic farmers in PGS processes and agroecological farming methods.

Developing the short organic supply chain with independent retailers and markets committed to enabling smallholder farmers’ access through a fair pricing model.

Developing an understanding and commitment to organic agriculture amongst all stakeholders in South Africa.

A commitment to community, the environment and future generations.

To expand the awareness and uptake of organic farming methods, PGS SA in partnership with the South African Organic Sector Organisation (SAOSO) is training and supporting 20 Pollinators or community practitioners to establish new PGS groups in South Africa.

You can find our pollinators here.

Stories from the Ground

by PGS SA | Sep 11, 2023 | News from the ground, PGS News

Urban Oasis Urban Oasis, a six-part video series, looks at community food gardening projects that employ, up-skill, and feed local residents. https://specialprojects.news24.com/urban-oasis/index.html specialprojects.news24.com

#ChooseOrganic this September – it’s good for you, it’s good for the planet

by PGS SA | Sep 7, 2023 | News from the ground, PGS News

Many stories of inspiration despite hardship are folded into the Valley of a Thousand Hills

by PGS SA | Aug 11, 2023 | News from the ground, PGS News, Uncategorized

Activists call for waiver on markups of 10 nutritious items after rice, flour and sugar prices spike

by PGS SA | Jul 14, 2023 | News from the ground

Planting seeds of organic agriculture growth in Limpopo

Organic farming in South Africa has industry partners capacitate the PGS SA Pollinator Programme

by PGS SA | Dec 8, 2022 | News from the ground

As part of the Knowledge Hub for Organic Agriculture in Southern Africa (KHSA) programme in South Africa, in country partners the South African Organic Sector Organisation (SAOSO) and Participatory Guarantee Systems South Africa (PGS SA) launched a week-long training...

World Organic Day 2022

by PGS SA | Dec 7, 2022 | News from the ground, PGS News

18 October 2022 Down South Africa way, Participatory Guarantee System South Africa (PGS SA) celebrated World Organic Day 2022 by hosting local farmers markets in various parts of the country. The day was an opportunity for the PGS groups to showcase fresh produce they...

Open letter to Minister Thoko Didiza

by PGS SA | Dec 5, 2022 | News from the ground, PGS News

Open letter to Minister Thoko Didiza Call for an agroecology strategy and programme in the Department of Agriculture, Land Reform and Rural Development 2 December 2022 Ms Thoko Didiza, Minister of Agriculture, Land Reform and Rural Development Download...

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## Organic Certification - PGS

`https://www.pgssa.org.za/organic-certification/` - PGS SA - fetched 2026-11-05 - 615 words

*Why this page is here:* PGS versus third-party certification, explained by the body

Organic certification offers assurance that consumers can trust . The South African Organic Certification Landscape is a document describing the use of logos and seals in the organic sector.

The South African organic certification landscape

A first party organic certification is a “self-claim” which is not verified by outside parties. It covers a direct relationship between a farmer and a consumer whereby you visit the farm or discuss with the farmer and are satisfied with his claims.

Second party organic certification in South Africa is assured by a Participatory Guarantee System (PGS) and works withshort supply chains. PGS provides a locally focused quality assurance system that certifies producers based on active participation. PGS SA is a SAOSO partner.

Third party organic certification is required for long supply chains and export. The processes are certified annually by an accredited certifying body (ACB) to specific organic standards.

SAOSO has developed a local Standard for Organic Production and Processing which is included in the IFOAM Family of Standards. Chapters 1, 2 and 3 are applicable to all crop and animal production systems. Chapters 8, 9 and 10 are applicable to all systems, including processing. Appendix 9 deals specifically with PGS systems.

The SAOSO organic standard is verified locally. Consumers can recognise compliance with the standard represented by these two trademarked logos.

Farmers who are already producing a surplus of organic produce and organized as an Organic farmer Association (OFO), and wanting to aggregate and sell their produce to a local market where there is consumer demand for organic produce, get together to form a PGS group. The PGS group agrees on operational procedures and their Basic Production Principles, based on an internationally accepted standard, against which farmers will be assessed. The members sign pledges and formally establish the PGS group at a general meeting. The group completes a self-assessment form (like a status report), shares the required information with PGS SA and pays an annual membership fee. It will also be asked to share the database of its certified members annually.

The group conducts farm visits, in which both consumers and farmers have a say, and on approval grants certificates to its farmer members in the relevant category. Farmers may label their products accordingly. They can use either of two seals:

PGS Organic In-Conversion Farmers who cannot support/ attest to the organic history of the land or who are converting from chemical to organic agriculture may be granted this seal by their group.

If you would like to consider being third party certified, please go through this infographic.

Questions for farmers thinking about third party organic certification.

Farmers who are already producing a surplus of organic produce and organized as an Organic farmer Association (OFO), and wanting to aggregate and sell their produce to a local market where there is consumer demand for organic produce, get together to form a PGS group.The PGS group agrees on operational procedures and their Basic Production Principles, based on an internationally accepted standard, against which farmers will be assessed. The members sign pledges and formally establish the PGS group at a general meeting. The group completes a self-assessment form (like a status report), shares the required information with PGS SA and pays an annual membership fee. It will also be asked to share the database of its certified members annually.

The group conducts farm visits, in which both consumers and farmers have a say, and on approval grants certificates to its farmer members in the relevant category. Farmers may label their products accordingly.They can use either of two seals:

South African Organic Certification Landscape

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## Why Organic - PGS

`https://www.pgssa.org.za/why-organic/` - PGS SA - fetched 2026-11-05 - 461 words

*Why this page is here:* the pitch

Organic is a lifestyle, a philosophy and a science. It is a way of living in the world that is in harmony with nature. Healthy soils, ecosystems and people, are supported by organic farming practices.

Organic agriculture has been proven to be more efficient in times of climate change and drought and far better suited to the large majority farmers who choose to farm in an ecologically-sound manner.

Organic food is better for your health!

Research has shown that food that is grown organically is better for our health.

Organic crops contain higher levels of important antioxidants, minerals, and vitamins such as Vitamin C, iron, magnesium, and phosphorus that are better for our bodies and our general immunity.

Organic food also minimises our exposure to pesticides and toxins. Children are especially vulnerable to pesticides and avoiding this in their diets is beneficial.

Why should you buy organic?

Food that is farmed organically is:

More nutritious and tasty

Farmed in a way that reduces pollution and protects the soil and water

From a system that preserves ecosystems and biodiversity

Fostering social justice and fairness in the foodsystem

Organic farming is better for the environment.

Organic farming is a win-win for people, animals and the planet. It takes a Gaia holistic approach that works with Mother Nature to grow healthy, nutritious food while at the same time preserving earth’s natural ecosystems.

It offers a solution to some of our greatest problems: climate change, food insecurity and biodiversity loss.

Ways that organic farming positively impacts the environment:

Eliminates persistent and harmful pesticides from entering the environment

Builds healthy top soil and prevents erosion

Supports water conservation and water health

Reduces carbon dioxide and helps slow climate change

Preserves natural habitats for wildlife

Supports animal health and welfare

Doesn’t cause algae blooms or nitrate leaching from runoff from petroleum-based fertilisers often used in conventional farming

Encourages biodiversity which protects humanity from future health threats.

Types of organic farming

There are many different terms used for farming methods that fall under the umbrella of organic agriculture. See our explanations here.

Organic farmers use best practices to produce healthy food without the use of synthetic and chemical inputs. Learn about land design, water management, soil health, companion planting, holistic livestock management and permitted inputs.

Local and global research

Data and research supporting organic agriculture versus conventional towards sustainable food systems and food sovereignty.

View Frequently Asked Questions About Organic Agriculture

Sign up for SAOSO’s monthly newsletter to stay informed about the latest organic news.

JOIN SOUTH AFRICA’S ORGANIC MOVEMENT.

Be a part of the sustainable food movement

Make A Recurring Or One-Time Gift

Join Us And Make A Difference

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## Pollinator Map - PGS

`https://www.pgssa.org.za/find-organic-food/` - PGS SA - fetched 2026-11-05 - 38 words

*Why this page is here:* the member-list surface

See where our PGS groups are located in South Africa

Click on the map to view interactive markers and information

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## Membership - PGS

`https://www.pgssa.org.za/membership/` - PGS SA - fetched 2026-11-05 - 460 words

*Why this page is here:* joining, and what it costs

PGS groups are constituted of farmers, consumers, market actors, and any other representatives of organisations who have a role to play in the local food system. You can join PGS SA as a farmer group.

Why choose PGS as a farmer?

PGS is a market access enabler for smallholder farmers who are committed to the principles of agroecology and organic farming methods. It is low-cost and focused on community strength and knowledge building.

Farmers are engaged in an ongoing learning process which helps improve their farming practices. PGS unifies smallholder farmers who have constituted themselves as an organic farmer organisation (OFO), fostering food and seed sovereignty, the protection of indigenous knowledge, and building partnerships with existing agricultural structures.

Why choose PGS as a consumer or retailer?

Consumers and market actors have the opportunity of being actively involved in PGS farm visit assessments enabling them to meet their farmers and experience the land where their food is grown. This affords the end-user the opportunity of understanding the real issues in the food supply chain and the importance of healthy, nutritious food grown in a responsible manner, and its connection to environmental and human health.

Participating consumers and market actors are needed to maintain a robust and transparent short food supply chain that supports its local smallholder farmers. Consumers and market actors are members in many PGS groups, not only buying products but also engaged in decision making and management.

What are the 3 steps to get your PGS going…

Introduction to Participatory Guarantee Systems in SA

Step-by-step guide on how to establish a PGS

How PGS works infographic

Elements and features of a PGS infographic

Photo and video guidelines

PGS SA membership requirements for PGS groups

PGS groups applying for membership to PGS SA need to pay an annual membership fee (as per the below fee structure) and complete the self-evaluation form. They also need to share their SoPS and the roster of farmer members in their PGS (annual updates required). All farm visits reports need to be uploaded to the PGS’ dedicated folder (link to be provided upon taking up the membership). Access to this PGS file is strictly restricted to the members of the PGS and PGS SA. Compliant PGS groups receive an annual PGS SA membership certificate.

– PGS SA membership form

– PGS SA self-evaluation form

– Database of farmers in your PGS

– Standard Operating Procedures

Once-off customisation of logo, seals and certificates

View our Calendar to see the next PGS visits and organic sector events in your area

Sign Up For PGS News And Stories

Stay informed about our farms and farmers, latest insights and best practices.

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## Resources - PGS

`https://www.pgssa.org.za/resources/` - PGS SA - fetched 2026-11-05 - 1358 words

*Why this page is here:* resource index

Here we answer all your questions about PGS, you can access our foundational documents, and download marketing materials.

Your Title Goes Here

Your content goes here. Edit or remove this text inline or in the module Content settings. You can also style every aspect of this content in the module Design settings and even apply custom CSS to this text in the module Advanced settings.

Participatory Guarantee Systems (PGSs) are community-based, second-party organic assurance mechanisms that serve as an alternative and complementary quality assurance system to third-party certification. The International Federation of Organic Agriculture Movements (IFOAM-Organics International) defines PGSs as “locally focused quality assurance systems”. They certify producers based on active participation of stakeholders and are built on a “foundation of trust, social networks and knowledge exchange”.

A PGS is a more accessible way for smallholder farmers to guarantee that their produce is grown organically and they are more inclusive than third-party certification because consumers, traders, distributors and processors can play a role. Importantly, PGSs are designed as a short supply chain, to nurture the local supply of organic produce getting into the local market, with an emphasis on giving the farmer a fair price and the localization of local food systems. They also give consumers the means to join informative, fun farm tours and to truly understand where their food comes form and to support their local farmers.

In a nutshell, PGS :

Is an accessible way for smallholder farmers to guarantee their produce is organic.

Reduces bureaucracy in the organic guarantee process.

Promotes equity and fairness throughout the production chain.

Promotes consumer access to organic products.

Is inclusive as consumers, traders, distributors and processors play an active role.

Supports food system transformation by building alternative and local food networks.

Enhances ownership of production standards and certification among PGS members.

Supports a continuous improvement of practices enhanced by knowledge exchange.

How do I get involved?

Join your local PGS: As a farmer, as a consumer or as a market space, the best way to get involved is to become a member of the PGS that is closest to you, by signing a pledge.

Approach your local PGS to see what support they need, which could entail helping with transporting farmers on farm visits, or helping with administration, marketing or planning events.

If no PGS exists in your area, you can mobilise your farmers and consumers and set one up, with the support of PGS SA and the PGS provincial representative.

You can also donate funds to PGS SA and earmark your funds for any specific support to growing the organic value chain in South Africa.

What is the role of retailers and consumers within PGS?

We need to drive demand for organically certified produce. Through the act of power that is buying, you directly support your local food system.

As a consumer, you should be looking out for the PGS seal and question your local producers on whether what they offer is organically grown, or if they do claim to be organic, you can tell them about PGS and the need to back their claims through certification. you can contribute to building a trust based, localised organic certification body that is run by farmers for farmers.

Market spaces need to support PGS certified farmers by allocating shelf space for their produce and by clearly labelling the produce that is PGS or third party organic certified, meaning that any other produce should be considered as conventional. Introducing differentiating labelling is key to building consumer trust and also creating demand for organic produce.

What PGS groups already exist in South Africa?

How can I start a PGS in my area?

A PGS is normally started when a group of stakeholders involved in the food chain see the benefits of the system or there is a need for organic assurance coming from the market.

As a first step, you should contact with the support of PGS SA and your PGS provincial representative to inquire whether any PGS group might be forming in your area. They might be able to put you in contact with other stakeholders also keen on starting a PGS in your area. If you need to start a PGS from scratch, you can use the resources available t which elucidate key principles and characteristics of a PGS, to guide you.

A key principle of PGS to remember when embarking on creating your PGS is that they are actively inclusive – seeking input from all stakeholders. Primary stakeholders include farmers and consumers, but farmers’ NGOs, consumer groups, environmental groups, and local and regional government agencies may all be involved in the PGS.

PGS SA will guide you through all the steps in setting up the PGS and you might be able to receive direct support from the PGS provincial representative.

What are the (in)direct costs associated with PGS and what involvement is expected of farmers?

PGS are characterised by lower direct costs as compared to individual third-party certification. Most PGS groups will ask for a small membership fee from their members (this is set by the PGS group itself) but the main currency required in operating a PGS is that of time; different PGS require different levels of farmer involvement. At a minimum, farmers (and consumers) are integrally involved in peer- reviews of each other’s operations. Farmers are also usually involved at the local level indirectly deciding on standards adopted, questions of certification as well as consequences for irregularities based on pre-agreed upon guidelines for managing non-compliance.

If farmers are not as involved in the operations of the PGS, this might entail bearing the costs of a PGS administrator or administration team, with each team member possibly assuming a different “portfolio” in running the PGS (membership, events, marketing, administrating farm visits – which can come at a small fee). Every PGS has a different model and PGS groups can learn a lot from one another.

What standard does a local PGS follow?

A PGS can follow any internationally accepted organic production standard. IN South Africa, PGS groups are encouraged to follow the SAOSO organic production standards, as this directly links its farmer members to the South African certification landscape.

What inputs are allowed in a PGS group?

As PGS groups certify their farmers against organic production standards, this means that PGS certified farmers are expected to follow the same rules AS THIRD PARTY certified farmers. The inputs accepted in the SAOSO standards for instance are listed in Annex 9.

However, given that the organic sector in South Africa is still in its infancy, the standard also allows for derogations from the standards.. This is particularly true for seeds and animal feed. The organic sector working group are currently working on a guidebook for PGS administrators in which the derogations from the standards will be explained with a specific focus on PGS and making the entry into organic farming more accessible.

How does PGS differ from third party certification?

Participatory Guarantee Systems (PGS) were formalized by the IFOAM Organic International as a recognized peer-review system whereby producers provide a formal guarantee to consumers that their products have been produced according to a recognized set of organic standards. This endorsement has low costs compared to third party. Third party certification for producers operating in a long-value chain and especially who are wanting to export their produce. The producer applies to a certification body (CB) for certification.

How to run a PGS Farm

How to set up a Farmers’ Market

See all our Webinars here

PGS has developed additional documents, such as a step-by-step guide on how to run farm visits, a farm assessment reporting template, checklists and guidelines to use during and to prep for farm visits, and a booklet for farm visit administrators (forthcoming). Please contact PGS SA at info@pgssa.org.za to become a PGS SA member and access these resources.

How PGS works infographic

Elements and features of a PGS infographic

Photo and video guidelines

GROWING THE ORGANIC SECTOR IN SOUTH AFRICA

by PGS SA | Apr 14, 2023 | Resources

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## Training Page - PGS

`https://www.pgssa.org.za/training-page/` - PGS SA - fetched 2026-11-05 - 96 words

*Why this page is here:* training offer

PGS SA and SAOSO jointly offer modular training courses to teach farmers about organic farming and take them through the Organic Farmer Journey . Jointly with INOFO, a group of farmers is assisted in forming an Organic Farming organisation (OFO), which then becomes the foundation through which a PGS group can be set up. Contact us to request a quote for your training needs.

Join our network of agroecological/organic trainers and technical advisers through the Yebo farmer App.

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## The Market - PGS

`https://www.pgssa.org.za/the-market/` - PGS SA - fetched 2026-11-05 - 66 words

*Why this page is here:* market-facing copy

Our PGS farmers supply to markets and retailers around the country.

Look for the PGS logo when shopping.

See our PGS groups around the country:

We are in the process of developing trade from PGS to PGS to enhance and grow the organic value chain. Watch this space.

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## 5th Session : How PGS groups organise for market and integrity of production - PGS

`https://www.pgssa.org.za/how-pgs-groups-organise-for-market-and-integrity-of-production/` - PGS SA - fetched 2026-11-05 - 380 words

*Why this page is here:* the most useful page here: a national body describing PGS procedure in prose

PGS > Blog > Webinars > 5th Session : How PGS groups organise for market and integrity of production

Jul 2, 2023 | Webinars

5th Session : How PGS groups organise for market and integrity of production

Make sure to have a look further down on A Quick Guide to Accessing and Using CC Tabs on YouTube To access these insightful sessions in various languages

Go ahead and dive in on the below speaker’s presentations

Sheryl Ozinsky and Audrey Wainwright, Orangezicht Farmers Market, Cape Town PGS, South Africa

Hamadi Djawara, Mali PGS

Matthew Purkis – Developing digital supply chains for food system transformation

Dive into Multilingual PGS Webinars: A Quick Guide to Accessing and Using CC Tabs on YouTube

Here’s a simple guide to effortlessly navigate and make the most of the Closed Captioning (CC) tabs, bringing these insightful sessions to you in various languages:

Spot the CC Icon: Once you click on the below and access the PGS webinar on YouTube, keep an eye out for the “CC” icon, usually located beneath the video player.

Activate Captions: Click on the “CC” icon to activate captions. This step will enable the CC feature to display subtitles for the ongoing webinar.

Choose Your Language: Select your preferred language from the available options within the CC settings. The magic begins as the captions now appear in your chosen language.

Enjoy Multilingual Webinars: Dive into the world of PGS webinars, now accessible in a language that resonates with you. Explore insights, gain knowledge, and connect with experts seamlessly.

The CC tabs pave the way for a richer, more inclusive webinar experience. Don’t miss out on the opportunity to engage with our content in the language that speaks to you. Happy learning!

#ChooseOrganic this September – it’s good for you, it’s good for the planet

Many stories of inspiration despite hardship are folded into the Valley of a Thousand Hills

Activists call for waiver on markups of 10 nutritious items after rice, flour and sugar prices spike

Planting seeds of organic agriculture growth in Limpopo

6th Session : Synergies between PGS and other development programmes or initiatives

Global organic news (4)

News from the ground (8)

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## 3rd Session Making PGS Groups sustainable - PGS

`https://www.pgssa.org.za/making-pgs-groups-sustainable/` - PGS SA - fetched 2026-11-05 - 361 words

*Why this page is here:* sustainability of a group, in prose

PGS > Blog > Webinars > 3rd Session Making PGS Groups sustainable

Jul 2, 2023 | Webinars

3rd Session Making PGS Groups sustainable

Make sure to have a look further down on A Quick Guide to Accessing and Using CC Tabs on YouTube To access these insightful sessions in various languages

Go ahead and dive in on the below speaker’s presentations

Konrad Hauptfleisch, Starfish Organic

Sylvaine LeMeilleur , CIRAD (France)

Ibrahima Seck, Organic Agriculture National Federation (FNAB) (Senegal)

Oxolo Mofokeng, Siyavuna PGS (South Africa)

Dive into Multilingual PGS Webinars: A Quick Guide to Accessing and Using CC Tabs on YouTube

Here’s a simple guide to effortlessly navigate and make the most of the Closed Captioning (CC) tabs, bringing these insightful sessions to you in various languages:

Spot the CC Icon: Once you click on the below and access the PGS webinar on YouTube, keep an eye out for the “CC” icon, usually located beneath the video player.

Activate Captions: Click on the “CC” icon to activate captions. This step will enable the CC feature to display subtitles for the ongoing webinar.

Choose Your Language: Within the CC settings, select your preferred language from the available options. The magic begins as the captions now appear in your chosen language.

Enjoy Multilingual Webinars: Dive into the world of PGS webinars, now accessible in a language that resonates with you. Explore insights, gain knowledge, and connect with experts seamlessly.

The CC tabs pave the way for a richer, more inclusive webinar experience. Don’t miss out on the opportunity to engage with our content in the language that speaks to you. Happy learning!

#ChooseOrganic this September – it’s good for you, it’s good for the planet

Many stories of inspiration despite hardship are folded into the Valley of a Thousand Hills

Activists call for waiver on markups of 10 nutritious items after rice, flour and sugar prices spike

Planting seeds of organic agriculture growth in Limpopo

6th Session : Synergies between PGS and other development programmes or initiatives

Global organic news (4)

News from the ground (8)

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now

## 1st Session :The challenge of honouring the fundamentals of PGS - PGS

`https://www.pgssa.org.za/the-challenge-of-honouring-the-fundamentals-of-pgs/` - PGS SA - fetched 2026-11-05 - 358 words

*Why this page is here:* self-critical prose - the voice a committee recognises

PGS > Blog > Webinars > 1st Session :The challenge of honouring the fundamentals of PGS

Jul 2, 2023 | Webinars

1st Session :The challenge of honouring the fundamentals of PGS

Make sure to have a look further down on A Quick Guide to Accessing and Using CC Tabs on YouTube To access these insightful sessions in various languages

Go ahead and dive in on the below speaker’s presentations

Konrad Hauptfleisch_ Starfish organic_presentation

Audrey Wainwright_Cape Town PGS_presentation

Olawumi Benedict_ PGS Ghana_presentation

Dive into Multilingual PGS Webinars: A Quick Guide to Accessing and Using CC Tabs on YouTube

Here’s a simple guide to effortlessly navigate and make the most of the Closed Captioning (CC) tabs, bringing these insightful sessions to you in various languages:

Spot the CC Icon: Once you click on the below and access the PGS webinar on YouTube, keep an eye out for the “CC” icon, usually located beneath the video player.

Activate Captions: Click on the “CC” icon to activate captions. This step will enable the CC feature to display subtitles for the ongoing webinar.

Choose Your Language: Within the CC settings, select your preferred language from the available options. The magic begins as the captions now appear in your chosen language.

Enjoy Multilingual Webinars: Dive into the world of PGS webinars, now accessible in a language that resonates with you. Explore insights, gain knowledge, and connect with experts seamlessly.

The CC tabs pave the way for a richer, more inclusive webinar experience. Don’t miss out on the opportunity to engage with our content in the language that speaks to you. Happy learning!

#ChooseOrganic this September – it’s good for you, it’s good for the planet

Many stories of inspiration despite hardship are folded into the Valley of a Thousand Hills

Activists call for waiver on markups of 10 nutritious items after rice, flour and sugar prices spike

Planting seeds of organic agriculture growth in Limpopo

6th Session : Synergies between PGS and other development programmes or initiatives

Global organic news (4)

News from the ground (8)

Looks like you haven't made a choice yet.

Got a discount code?

Your cart is empty. Shop now


---

# Cape PGS

## Western Cape Farmer's PGS – Western Cape Farmer's PGS

`https://pgs.org.za/` - Cape PGS - fetched 2026-11-05 - 695 words

*Why this page is here:* a sibling group in the same province

About the Western Cape Farmers’ PGS

The Western Cape Farmers’ PGS (WCF-PGS) is a farmer-led collective that supports and offers PGSSA and SAOSO-standard verification of organic farming through trust, transparency, and peer-to-peer collaboration.

Formed by a small group of committed growers, the WCF-PGS offers a community-based alternative to third-party organic certification. Each farm is visited at least once a year – not only to uphold standards, but also to share knowledge and strengthen connections.

Providing a high standard of regulation and support for organic farmers, recognised by SAOSO, we work to build a more just, ecological, and farmer-driven food system across the Western Cape.

The Western Cape Farmers PGS (WCF-PGS) was founded by Francois and Henriette Malan, Anique Van Der Vlugt and Charl Hubner.

Globally, Particapatory Guarantee Systems (PGSs) consist of groups of farmers that provide a support and verification network for organic agriculture in a specific area and is used by small farmers to establish organic credibility, traceability and verification for agricultural practices, without incurring the costs of third-party certification. The standards for forming a PGS was established by the International Federation of Organic Movements (IFOAM) and put into practice sometime around 2004 and has since grown internationally into more than …. groups of farmers and consumers working together to develop and maintain organic production standards on par with the highest internationally recognised organic agriculture requirements.

The WCF-PGS was formed at a time when organic agriculture was relatively unknown in South Africa and quite poorly understood, in an effort to both provide security and standardisation for consumers and retailers of organic produce, as well as to provide cost-free organic certification and support for farmers.

Considering that organic agriculture is still not nationally regulated in South Africa (meaning that there is no legal requirement on what a retailer can call ‘organic’), the importance of having groups like the WCF-PGS to describe and verify organic production standards is of utmost importance.

The Western-Cape Farmers PGS remains the oldest and one of the only farmer-run PGS groups in South Africa, providing a high standard of regulation and support for organic farming recognised by consumers, retailers and NGOs (eg. PGSSA and SAOSO) alike.

Verify which farmers have been certified by the Western Cape Farmers’ PGS by viewing our listings.

The Western Cape Farmers’ PGS is a non-profit collective of individual farms and or farmers who practice organic farming in accordance with the South African Organic Sector Organisation, as guided by the International Federation of Organic Agriculture Movements.

How to Become a Member?

Any farming operation is eligible for membership to the WCF-PGS, pending a farm assessment and evaluated compliance with organic standards. If you are interested in joining the WCF-PGS, you can contact us at info@pgs.org.za and also view our farm assessment inspection form here WCF-PGS Inspection Form.pdf. PGS groups are by their nature collaborative and supportive, not punitive, so if you are uncertain whether you qualify for organic accreditation, don’t hesitate to reach out and get free, professional advice and consultation from one of our senior farmer members.

*The WCF-PGS remains a cost-free initiative, in order to maintain the spirit of open-source and ideals-driven collaboration to further organic agriculture.

Join as a Consumer or Retailer

Any person or group can join the WCF-PGS mailing list in order to stay up-to-date on our yearly farm visits, which are open and free to attend for anyone. We facilitate transparency and participation by making all of our processes open to all interested parties.

Join as a consumer / retailer

We follow the South African Organic Sector Organisation (SAOSO) Standard for Organic Production and Processing. These rigorous guidelines align with internationally recognised criteria – SAOSO’s standard is officially included in the IFOAM Family of Standards, drawing directly from IFOAM’s norms.

Each farm is evaluated against these standards during annual peer visits, ensuring that organic practices meet high benchmarks for ecological health, fairness, and food safety, while fostering shared learning and trust across our community.

View SAOSO PGS Standards

Rooted in community – these are the people steering the WCF-PGS.

Botanical Taste Fresh Produce

Western Cape Farmer's PGS

Dig deeper into our resources, or find out more about the broader organic movement.

## Our Farmers – Western Cape Farmer's PGS

`https://pgs.org.za/farmers/` - Cape PGS - fetched 2026-11-05 - 205 words

*Why this page is here:* how a peer group lists its farmers

Nevau Levanon2024-06-26 22:44:342025-06-12 18:51:40Botanical Taste

Nevau Levanon2024-06-26 22:39:592024-11-27 10:09:37Sababa Farm

Nevau Levanon2024-06-26 22:33:432024-11-27 10:00:16Tierhoek Organic Farm

Nevau Levanon2024-06-26 22:23:562024-11-27 09:46:35Vredenhof Organic Estate

Nevau Levanon2024-06-26 22:14:422024-11-27 09:29:48Eric Swarts Farming

Nevau Levanon2024-06-26 22:09:182024-11-27 09:47:38Spier Food Garden

Nevau Levanon2024-06-26 22:04:512026-01-13 16:19:51Mountain View

We’re proud to stand alongside an incredible network of farmers who form the heart of the Western Cape Farmers’ PGS. From the valleys of Tulbagh to the slopes of Piket-bo-berg and Citrusdal, and across the fields of Stellenbosch and Robertson, our members are cultivating more than just food – they’re growing a movement rooted in trust, transparency, and ecological care.

Each participating farm is visited and peer-reviewed at least once a year. These farm visits are always a highlight – part inspection, part shared learning, and part networking experience. They’re a chance to walk the land together, ask questions, share knowledge, and strengthen the relationships that hold this community together.

Whether they’re tending vegetables, orchards, or herbs, our farmers are active participants in shaping a more resilient, ethical food system – and we’re deeply grateful for the time, energy, and generosity they bring to the table.

Are you a farmer interested in joining our PGS?

Looking for other PGS groups elsewhere?

Go to PGS South Africa

## Documentation – Western Cape Farmer's PGS

`https://pgs.org.za/documentation/` - Cape PGS - fetched 2026-11-05 - 63 words

*Why this page is here:* what a peer group publishes as its rules

You are here: Home1 / Documentation

Western Cape Farmers’ PGS Documentation

Here you’ll find all the key documents that guide and support the work of the WCF-PGS – from our organic standards and forms to our constitution, and guidelines. Whether you’re a current member, a prospective farmer, or simply curious about how we operate, this is the place to dig into the details.

## Resources – Western Cape Farmer's PGS

`https://pgs.org.za/resources/` - Cape PGS - fetched 2026-11-05 - 66 words

*Why this page is here:* peer resource page

You are here: Home1 / Resources

External Resources & Links

Helpful links, articles, and educational materials for anyone wanting to learn more about organic farming, Participatory Guarantee Systems (PGS), and the broader organic movement in South Africa and beyond. Whether you’re just starting out or deepening your practice, we’ve gathered resources to inspire, inform, and connect you to the wider organic community.

Click to visit website

## Contact – Western Cape Farmer's PGS

`https://pgs.org.za/contact/` - Cape PGS - fetched 2026-11-05 - 70 words

*Why this page is here:* peer contact page

You are here: Home1 / Contact

For all general enquiries, please feel free to get in touch with us.

If you would like to join the PGS as a farmer or find out more, please see below.

Looking for our documentation or forms?

View our useful resources and links:

Are you a farmer interested in joining our PGS?

Looking for other PGS groups elsewhere?

Go to the PGS South Africa


---

# IFOAM

## Participatory Guarantee Systems | IFOAM

`https://www.ifoam.bio/our-work/how/standards-certification/participatory-guarantee-systems` - IFOAM - fetched 2026-11-05 - 434 words

*Why this page is here:* the definition this site quotes

Skip to main content

IFOAM - Organics International Network

Our regional bodies, national groups and sector platforms promoting organic throughout the world.

IFOAM Southern African Network

Intercontinental Network of Organic Farmers Organisations - INOFO

About IFOAM - Organics International Membership Directory

Participatory Guarantee Systems (PGS)

PGS initiatives are serving thousands of small organic producers and their consumers all over the world, and the numbers are increasing every year.

IFOAM - Organics International supports the development of PGS as an alternative and complementary tool to third-party certification within the organic sector and advocates for the recognition of PGS by governments.

We are the only organization collecting, compiling and publishing global data about PGS initiatives, please see our Statistics and Global Map of PGS initiatives.

We have the skills and resources to develop a tailor-made PGS training program for you and to provide you with support services and facilitation for building your PGS.

PGS are not to be confused with Internal Control Systems for group certification (ICS), another certification tool promoted by IFOAM to support smallholders.

"Participatory Guarantee Systems (PGS) are locally focused quality assurance systems. They certify producers based on active participation of stakeholders and are built on a foundation of trust, social networks and knowledge exchange."

This definition is available in Chinese/中文, Deutsch, Español, Français, Japanese/日本語 and Português.

Tailored Training & Advisory Services

IFOAM - Organics International also offers tailored training courses. Individuals interested in learning more about these offers can access our training page here for additional information.

New to PGS? Take a look at the most Frequently Asked Questions

Available Now: New Resources for PGS Advocates and Practitioners

Official PGS Recognition Program - A Service for PGS Initiatives

Discover all the PGS Initiatives Around the World in our Global Map

Catch up with all the PGS updates from the last ten years in our PGS Newsletter Archives

Participatory Guarantee Systems Toolkit

CFS54 Side Event | Local Solutions to Global Disruptions: Towards Healthy, Resilient and Agroecological Food Systems

In Memory of Marty Mesh (1953-2026)

Webinar: Beyond the label: How organic agriculture drives sustainable food systems

Breaking the Cycle of Chemicals and Debt: Organic Farming in Cambodia

Mr Keo Nov is a farmer in the Kandal Province of Cambodia. Together with his wife, they farm approximately 1,200 square meters of land, nearly a third of an acre.

Ms. Sieng: An Organic Entrepreneur in Cambodia!

Ms. Bun Sieng is an agronomist who has worked in rural communities for years. In 2012, she decided to start a business in order to link farmers to markets and give more people access to high- quality, locally produced vegetables

## Participatory Guarantee Systems Toolkit | IFOAM

`https://www.ifoam.bio/our-work/how/standards-certification/participatory-guarantee-systems/pgs-toolkit` - IFOAM - fetched 2026-11-05 - 1045 words

*Why this page is here:* the PGS toolkit

Skip to main content

IFOAM - Organics International Network

Our regional bodies, national groups and sector platforms promoting organic throughout the world.

IFOAM Southern African Network

Intercontinental Network of Organic Farmers Organisations - INOFO

About IFOAM - Organics International Membership Directory

Participatory Guarantee Systems Toolkit

This toolkit is aimed at anyone working to build truly sustainable, local food systems using Participatory Guarantee Systems (PGS).

Synergies with Community Supported Agriculture (CSA) and other solidarity based approaches are also mentioned in various of the publications here available

The Global Map of PGS initiatives

The PGS toolkit is composed of a series of tools:

"PGS Guidelines. How to develop and manage Participatory Guarantee Systems for Organic Agriculture"

These guidelines make the cornerstone of the toolkit. They highlight how, although developed independently in different countries and cultural contexts, PGS initiatives around the world share a common set of key elements and features. This revised edition of the PGS guidelines also propose a step by step approach for implementing PGS and introduce other important concepts like marketing and organisational arrangement.

"Policy Brief: How Governments can Support Participatory Guarantee Systems (PGS)"

Published for the first time in 2011, this Policy Brief on PGS is a landmark in IFOAM’s advocacy work. The document targets policy makers and advocates that wish to support PGS not only through recognition in their national organic regulatory systems, but also through different form of support aiming at promoting rather than regulating. For additional tips on how to ensure public support to PGS development you can check the dedicated section of the Guidelines for public support to organic agriculture.

Read More Télécharger Descarregar

Introducing stakeholders to the key background information, elements and features of PGS. Click here to see the overview of the training programme articulated in 4 modules. Individuals and initiatives interested in getting to know more about how to develop PGS are encouraged to contact IFOAM - Organics International to receive additional information.

Template Checklist for Peer Reviews for Crop Production

The peer review provides a mechanism through which compliance to the standards and norms can be verified by peers. It also provides for knowledge exchange whereby all involved parties learn more about the standards and each other’s farming practices. Users are encouraged get inspiration and adapt the content of this checklist according to their needs. Designing, testing and adopting the right peer review based on the standards adopted is a fundamental step for every PGS initiative and for those CSA initiatives introducing farm visits in their everyday activities. This checklist comes together with a basic list of objectives and requirements that should be addressed in each organic standards, with a focus on crop production. This list is taken from the COROS (Common Objectives and Requirements for Organic Standards - also called “IFOAM Standards Requirements”).

"Synergies between Community-Supported Agriculture (CSA) and Participatory Guarantee Systems (PGS)"

Usually, CSAs are implemented through a strong partnership between one or several producers and a group of consumers who pay upfront to receive a share of the harvest. This publication, produced by URGENCI and Miramap, analyses needs and benefits that motivate CSA groups to include a PGS in their structures. The reasons span from the necessity of preserving the meaning of the CSA concept (i.e. with respect to the founding principles of CSA) to continuously improve the agricultural practices and the solidarity partnership.

The PGS Brochure explains what the key elements and features of PGS are. The diversity of organic agriculture and guarantee systems, among which PGS, is highlighted. This Brochure is available in different languages: English, French, Spanish, Portuguese, Italian, German, Albanian, Japanese.

Showcases the needs and benefits for French CSAs to include formalised farm visits to better structure the partnership between consumers and producers and improve practices such as breaking free from chemical inputs dependence. The case study focuses on the experience of the Basque Country CSA network and was produced by Miramap.

Global Comparative PGS Case Study

The study shows that PGS is an important platform for the development of these social processes that in turn positively impact PGS initiatives in different ways, thereby improving the sustainability and impacts of the PGS. It finds that PGS has the potential to make a significant contribution to the reduction of food insecurity and to improved nutrition among farmers in rural areas.

Additional publications focusing on PGS case studies in:

Latin America (en Español)

Central and West Africa

These are some great videos that introduce the key PGS elements, present experiences of PGS initiatives worldwide and show how peer reviews are carried out.

There is a lot more to explore on our YouTube channel!

Display content from YouTube

PGS and Local Sustainable Food Systems

An Animated Journey into PGS

2019, CZ, EN, FR, GR, HU, SP

PGS: An introduction to Participatory Guarantee Systems

Shorter version with the main messages of our PGS Guide,

2016, CZ, EN, FR, GR, HU, IT, PT

The Peer Review of Nature et Progrès

2019, CZ, EN, FR, GR, HU

New: information on PGS in Dutch is also available! Check the case studies we prepared in collaboration with CSA Netwerk Netherlands: PGS Nederland

In partnership with the UN FAO, we have published case studies of PGS initiatives in Cambodia and Lao PDR

Read the story of one of our partners Pro-Bio Liga, who experimented with PGS and CSA : How Can We Build Local Food Systems? Experiences from the Czech Republic.

Most materials are available also in Czech, Greek and Hungarian on the website of our project partners.

To learn more about Participatory Guarantee Systems:

PGS basics: Learn about PGS and find answers to common questions

For PGS advocates and policymakers: Why invest in Participatory Guarantee Systems? (FAO and IFOAM - Organics International, 2019)

Access IFOAM PGS Media Library for more videos and publications in different languages.

See also our tailor made PGS trainings and consultancies page.

If you would like to be added to our PGS mailing list, contact pgs@ifoam.bio. The mailing list subscription enables you to keep up to date on future developments related to this topic.

To learn more about Community Supported Agriculture:

Visit Urgenci's CSA Training Hub created under the CSAct project, also funded by the Earmus Programme.

Download the publication "Be Part of CSA! Supporting Booklet for Training on Community Supported Agriculture".
