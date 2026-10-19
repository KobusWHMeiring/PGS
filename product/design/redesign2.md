<!DOCTYPE html>



<html class="scroll-smooth" lang="en"><head>

<meta charset="utf-8"/>

<meta content="width=device-width, initial-scale=1.0" name="viewport"/>

<title>Outeniqua PGS - Natural \&amp; Organic Assurance</title>

<!-- Google Fonts: Lora (literary transitional serif) \& Mulish (warm legible humanist sans) -->

<link href="https://fonts.googleapis.com" rel="preconnect"/>

<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>

<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600\&amp;family=Mulish:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400\&amp;display=swap" rel="stylesheet"/>

<!-- Tailwind CSS CDN with Forms \& Container-Queries -->

<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>

<!-- Tailwind Configuration for Sunlit Botanical Olive \& Ochre Variant -->

<script>

&#x20;   tailwind.config = {

&#x20;     theme: {

&#x20;       extend: {

&#x20;         colors: {

&#x20;           brand: {

&#x20;             forest: '#323E2A',

&#x20;             forestDark: '#242D1E',

&#x20;             forestDeep: '#1A2116',

&#x20;             moss: '#425337',

&#x20;             sage: '#8A6828',

&#x20;             sageLight: '#F3ECE0',

&#x20;             cream: '#FDFBF7',

&#x20;             creamWarm: '#F6F1E7',

&#x20;             sand: '#E6DECE',

&#x20;             charcoal: '#282622',

&#x20;             muted: '#6B665D',

&#x20;             tagGreen: '#EFE6CE',

&#x20;             tagGreenText: '#785012',

&#x20;             badgeBorder: '#D8CEBA',

&#x20;             ochre: '#B87B2E',

&#x20;             ochreDark: '#9C641E',

&#x20;             ochreLight: '#F9F1E2'

&#x20;           }

&#x20;         },

&#x20;         fontFamily: {

&#x20;           serif: \['Lora', 'Georgia', 'serif'],

&#x20;           sans: \['"Mulish"', 'system-ui', '-apple-system', 'sans-serif'],

&#x20;         }

&#x20;       }

&#x20;     }

&#x20;   }

&#x20; </script>

<!-- BEGIN: Custom Styles -->

<style data-purpose="custom-typography">

&#x20;   body {

&#x20;     font-feature-settings: "cv02", "cv03", "cv04", "cv11";

&#x20;     text-rendering: optimizeLegibility;

&#x20;     -webkit-font-smoothing: antialiased;

&#x20;   }

&#x20;   .serif-title {

&#x20;     font-family: 'Lora', Georgia, serif;

&#x20;     letter-spacing: -0.015em;

&#x20;   }

&#x20; </style>

<style data-purpose="contour-background">

&#x20;   /\* Sunlit Olive \& Botanical canopy gradient with warm ochre undertones \*/

&#x20;   .hero-contour-bg {

&#x20;     background: radial-gradient(circle at 50% 18%, #415136 0%, #303C28 55%, #20281B 100%);

&#x20;     position: relative;

&#x20;   }

&#x20;   .hero-contour-bg::before {

&#x20;     content: "";

&#x20;     position: absolute;

&#x20;     inset: 0;

&#x20;     background-image: 

&#x20;       radial-gradient(ellipse 90% 45% at 50% 95%, rgba(184, 123, 46, 0.22) 0%, transparent 70%),

&#x20;       radial-gradient(ellipse 80% 35% at 50% 85%, rgba(94, 117, 78, 0.35) 0%, transparent 65%),

&#x20;       radial-gradient(ellipse 110% 40% at 50% 75%, rgba(55, 70, 46, 0.45) 0%, transparent 75%);

&#x20;     pointer-events: none;

&#x20;   }

&#x20; </style>

<!-- END: Custom Styles -->

</head>

<body class="bg-brand-cream text-brand-charcoal font-sans antialiased selection:bg-brand-sageLight selection:text-brand-forestDark">

<!-- BEGIN: SiteNavigation -->

<header class="sticky top-0 z-50 bg-brand-cream/95 backdrop-blur-md border-b border-brand-sand transition-all" data-purpose="site-header">

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">

<!-- Brand Logo -->

<a aria-label="Outeniqua PGS Home" class="flex items-center gap-3 group" href="#">

<div class="w-10 h-10 rounded-full bg-brand-forest text-brand-cream flex items-center justify-center font-serif text-lg font-bold shadow-sm ring-2 ring-brand-forest/10 group-hover:scale-105 transition-transform">

<!-- Stylized Sprout / Leaf SVG -->

<svg class="w-5 h-5 text-amber-300" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M12 19V6m0 0l-4 4m4-4l4 4M5 20c0-4 3.5-7 7-7s7 3 7 7" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<div>

<span class="block text-sm font-bold tracking-tight text-brand-charcoal font-serif uppercase leading-none">Outeniqua PGS</span>

<span class="text-\[10px] uppercase tracking-widest text-brand-muted font-medium">Natural \&amp; Organic</span>

</div>

</a>

<!-- Primary Navigation Links -->

<nav aria-label="Main Navigation" class="hidden md:flex items-center space-x-7 text-xs font-semibold tracking-wider text-brand-charcoal/80 uppercase">

<a class="hover:text-brand-ochre transition-colors" href="#organics">Organics</a>

<a class="hover:text-brand-ochre transition-colors" href="#how-it-works">How it works</a>

<a class="hover:text-brand-ochre transition-colors" href="#documents">Documents</a>

<a class="hover:text-brand-ochre transition-colors" href="#members">Members</a>

<a class="hover:text-brand-ochre transition-colors" href="#contact">Contact</a>

</nav>

<!-- Right Hand Actions (Language toggle + Membership CTA) -->

<div class="flex items-center space-x-4">

<!-- Language Switcher -->

<div class="hidden sm:inline-flex items-center p-1 bg-brand-sand/60 rounded-full text-xs font-medium text-brand-muted border border-brand-sand">

<span class="px-2.5 py-0.5 rounded-full bg-white text-brand-forest font-semibold shadow-xs">EN</span>

<a class="px-2 py-0.5 hover:text-brand-forest" href="#">AF</a>

</div>

<!-- Call to Action Button -->

<a class="inline-flex items-center justify-center px-4 py-2 rounded-full text-xs font-semibold tracking-wide text-brand-cream bg-brand-forest hover:bg-brand-forestDark transition-all duration-200 shadow-sm hover:shadow hover:-translate-y-0.5" href="#how-it-works">

&#x20;         Become a member

&#x20;       </a>

</div>

</div>

</header>

<!-- END: SiteNavigation -->

<main>

<!-- BEGIN: HeroSection -->

<section class="hero-contour-bg text-brand-cream pt-24 pb-28 px-4 sm:px-6 lg:px-8 overflow-hidden relative" data-purpose="hero-banner">

<div class="max-w-4xl mx-auto text-center relative z-10">

<!-- Region Pill -->

<div class="inline-block mb-6">

<span class="inline-flex items-center px-3.5 py-1 rounded-full text-\[11px] font-semibold tracking-widest uppercase bg-amber-200/10 text-amber-200 backdrop-blur-sm border border-amber-300/25">

&#x20;           Participatory Guarantee System · Western Cape

&#x20;         </span>

</div>

<!-- Main Headline -->

<h1 class="serif-title text-4xl sm:text-5xl md:text-6xl font-normal leading-\[1.12] text-white tracking-tight mb-7">

&#x20;         Organic assurance built by <br class="hidden sm:block"/>

<span class="italic font-normal text-amber-200">farmers, for farmers.</span>

</h1>

<!-- Subheading Paragraph -->

<p class="max-w-2xl mx-auto text-base sm:text-lg leading-relaxed text-brand-cream/85 font-normal mb-10">

&#x20;         We are a locally focused quality assurance group. Members assess one another against the SAOSO organic standard, on each other’s farms, in the open — built on trust, social networks and knowledge exchange, not a distant inspector.

&#x20;       </p>

<!-- CTA Buttons -->

<div class="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4 mb-14">

<a class="w-full sm:w-auto px-7 py-3 rounded-full text-xs font-semibold tracking-wider uppercase text-brand-forestDark bg-brand-cream hover:bg-white transition-all shadow-md hover:shadow-lg" href="#how-it-works">

&#x20;           How it works

&#x20;         </a>

<a class="w-full sm:w-auto px-7 py-3 rounded-full text-xs font-semibold tracking-wider uppercase text-brand-cream border border-brand-cream/35 hover:bg-brand-cream/10 transition-all backdrop-blur-xs" href="#ask-standard">

&#x20;           Ask the standard

&#x20;         </a>

</div>

<!-- International Federation Accreditation Note -->

<div class="pt-6 border-t border-white/10 max-w-lg mx-auto">

<p class="text-xs text-brand-cream/65 font-light leading-relaxed">

&#x20;           A PGS is defined by IFOAM-Organics International as a locally focused quality assurance system.

&#x20;         </p>

</div>

</div>

</section>

<!-- END: HeroSection -->

<!-- BEGIN: MetricKeyFactsRibbon -->

<section class="border-b border-brand-sand bg-\[#F3ECE0]" data-purpose="key-facts-ribbon">

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">

<!-- Modular pill cards with soft divider borders -->

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">

<div class="bg-brand-cream/80 border border-brand-sand/80 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-2xs hover:bg-white transition-colors">

<div class="w-2.5 h-2.5 rounded-full bg-brand-ochre shrink-0"></div>

<div class="text-left">

<h4 class="serif-title text-base sm:text-lg font-semibold text-brand-forest leading-tight">PGS South Africa</h4>

<p class="text-xs text-brand-muted mt-0.5">Member group</p>

</div>

</div>

<div class="bg-brand-cream/80 border border-brand-sand/80 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-2xs hover:bg-white transition-colors">

<div class="w-2.5 h-2.5 rounded-full bg-brand-ochre shrink-0"></div>

<div class="text-left">

<h4 class="serif-title text-base sm:text-lg font-semibold text-brand-forest leading-tight">SAOSO v2.1 (2026)</h4>

<p class="text-xs text-brand-muted mt-0.5">The standard we assess against</p>

</div>

</div>

<div class="bg-brand-cream/80 border border-brand-sand/80 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-2xs hover:bg-white transition-colors">

<div class="w-2.5 h-2.5 rounded-full bg-brand-ochre shrink-0"></div>

<div class="text-left">

<h4 class="serif-title text-base sm:text-lg font-semibold text-brand-forest leading-tight">6 basic elements</h4>

<p class="text-xs text-brand-muted mt-0.5">The PGS way of working</p>

</div>

</div>

<div class="bg-brand-cream/80 border border-brand-sand/80 rounded-2xl px-5 py-4 flex items-center gap-4 shadow-2xs hover:bg-white transition-colors">

<div class="w-2.5 h-2.5 rounded-full bg-brand-ochre shrink-0"></div>

<div class="text-left">

<h4 class="serif-title text-base sm:text-lg font-semibold text-brand-forest leading-tight">R100 / year</h4>

<p class="text-xs text-brand-muted mt-0.5">Farmer \&amp; consumer membership</p>

</div>

</div>

</div>

</div>

</section>

<!-- END: MetricKeyFactsRibbon -->

<!-- BEGIN: SixBasicElements -->

<section class="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto" data-purpose="six-elements" id="organics">

<!-- Section Heading -->

<div class="max-w-2xl mb-12">

<span class="text-xs font-bold tracking-widest uppercase text-brand-sage block mb-2">The PGS</span>

<h2 class="serif-title text-3xl sm:text-4xl text-brand-forestDark font-normal tracking-tight mb-4">

&#x20;         Guided by six basic elements

&#x20;       </h2>

<p class="text-sm sm:text-base text-brand-muted leading-relaxed">

&#x20;         A Participatory Guarantee System is not an inspection regime. It is a group of peers who hold each other to a shared standard. These six elements are what make it a PGS rather than a certificate bought from an agency.

&#x20;       </p>

</div>

<!-- 6 Elements Grid: balanced 2x3 grid with full-bleed subtle border division -->

<div class="bg-white rounded-2xl border border-brand-sand overflow-hidden shadow-xs divide-y divide-brand-sand/70 mb-10">

<div class="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-brand-sand/70">

<!-- Element 1: Shared Vision -->

<article class="p-8 hover:bg-brand-cream/40 transition-colors">

<div class="w-10 h-10 rounded-lg bg-brand-sageLight/70 text-brand-ochre flex items-center justify-center mb-5">

<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<h3 class="serif-title text-lg font-bold text-brand-forestDark mb-2">Shared Vision</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;           Members share a common goal based on a shared need, and collectively embrace the principles of PGS and organic agriculture.

&#x20;         </p>

</article>

<!-- Element 2: Trust -->

<article class="p-8 hover:bg-brand-cream/40 transition-colors">

<div class="w-10 h-10 rounded-lg bg-brand-sageLight/70 text-brand-ochre flex items-center justify-center mb-5">

<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<h3 class="serif-title text-lg font-bold text-brand-forestDark mb-2">Trust</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;           An integrity-based approach. Trust and integrity form the ethical basis of the system, verified through transparency.

&#x20;         </p>

</article>

</div>

<div class="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-brand-sand/70">

<!-- Element 3: Horizontality -->

<article class="p-8 hover:bg-brand-cream/40 transition-colors">

<div class="w-10 h-10 rounded-lg bg-brand-sageLight/70 text-brand-ochre flex items-center justify-center mb-5">

<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<h3 class="serif-title text-lg font-bold text-brand-forestDark mb-2">Horizontality</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;           A flat, equitable organisational structure, developed and managed by peers rather than a top-heavy management. All are responsible.

&#x20;         </p>

</article>

<!-- Element 4: Transparency -->

<article class="p-8 hover:bg-brand-cream/40 transition-colors">

<div class="w-10 h-10 rounded-lg bg-brand-sageLight/70 text-brand-ochre flex items-center justify-center mb-5">

<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" stroke-linecap="round" stroke-linejoin="round"></path>

<path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<h3 class="serif-title text-lg font-bold text-brand-forestDark mb-2">Transparency</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;           The system is open to public, stakeholder and peer scrutiny at all levels. Meeting agendas and standard reviews are accessible.

&#x20;         </p>

</article>

</div>

<div class="grid grid-cols-1 md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-brand-sand/70">

<!-- Element 5: Participatory -->

<article class="p-8 hover:bg-brand-cream/40 transition-colors">

<div class="w-10 h-10 rounded-lg bg-brand-sageLight/70 text-brand-ochre flex items-center justify-center mb-5">

<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<h3 class="serif-title text-lg font-bold text-brand-forestDark mb-2">Participatory</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;           Members participate in developing and managing the process and procedures the group owns, controls and determines collectively.

&#x20;         </p>

</article>

<!-- Element 6: Learning Process -->

<article class="p-8 hover:bg-brand-cream/40 transition-colors">

<div class="w-10 h-10 rounded-lg bg-brand-sageLight/70 text-brand-ochre flex items-center justify-center mb-5">

<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<h3 class="serif-title text-lg font-bold text-brand-forestDark mb-2">Learning Process</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;           Assessments and site visits focus on skills and knowledge exchange — traditional knowledge and innovation, soil, climate and market.

&#x20;         </p>

</article>

</div>

</div>

<!-- IFOAM Citation Box (delicate left-bordered layout) -->

<div class="border-l-4 border-brand-ochre bg-white p-6 sm:p-7 rounded-r-xl border-y border-r border-brand-sand shadow-xs">

<blockquote class="italic font-serif text-brand-charcoal text-sm sm:text-base leading-relaxed">

&#x20;         “Participatory Guarantee Systems are locally focused quality assurance systems. They certify producers based on active participation of stakeholders and are built on a foundation of trust, social networks and knowledge exchange.”

&#x20;       </blockquote>

<p class="text-xs text-brand-muted mt-2 font-medium">

&#x20;         — IFOAM–Organics International, quoted in the SA Organic Certification Landscape

&#x20;       </p>

</div>

</section>

<!-- END: SixBasicElements -->

<!-- BEGIN: HowItWorks -->

<section class="py-20 bg-brand-creamWarm border-y border-brand-sand" data-purpose="membership-procedure" id="how-it-works">

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

<!-- Header -->

<div class="max-w-2xl mb-12">

<span class="text-xs font-bold tracking-widest uppercase text-brand-sage block mb-2">Membership Procedure</span>

<h2 class="serif-title text-3xl sm:text-4xl text-brand-forestDark font-normal tracking-tight mb-3">

&#x20;           How it works

&#x20;         </h2>

<p class="text-sm text-brand-muted leading-relaxed">

&#x20;           Every prospective farmer and producer member follows the same path, in the same order. It is set out in the group’s Principles, Policies and Procedures.

&#x20;         </p>

</div>

<!-- 6 Step Progression Flow: structured numbered card matrix with progress indicators -->

<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">

<!-- Step 1 -->

<div class="bg-white p-6 rounded-xl border border-brand-sand flex flex-col justify-between shadow-2xs relative">

<div>

<div class="flex items-center justify-between mb-3">

<span class="text-\[11px] font-bold text-brand-ochre uppercase tracking-wider">Step 1</span>

<span class="w-6 h-6 rounded-full bg-brand-sageLight/60 text-brand-ochre flex items-center justify-center font-bold text-xs">1</span>

</div>

<h3 class="font-serif font-bold text-lg text-brand-forestDark mb-2">Apply</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;               Approach the group as a prospective farmer or producer member.

&#x20;             </p>

</div>

<div class="mt-6 pt-3 border-t border-brand-sand/60 flex items-center justify-between text-\[11px] text-brand-muted font-medium">

<span>Initial contact</span>

<span class="text-brand-ochre text-sm font-bold">→</span>

</div>

</div>

<!-- Step 2 -->

<div class="bg-white p-6 rounded-xl border border-brand-sand flex flex-col justify-between shadow-2xs relative">

<div>

<div class="flex items-center justify-between mb-3">

<span class="text-\[11px] font-bold text-brand-ochre uppercase tracking-wider">Step 2</span>

<span class="w-6 h-6 rounded-full bg-brand-sageLight/60 text-brand-ochre flex items-center justify-center font-bold text-xs">2</span>

</div>

<h3 class="font-serif font-bold text-lg text-brand-forestDark mb-2">Pledge</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;               Sign the farmer member pledge. A recorded verbal pledge is accepted where reading is a barrier.

&#x20;             </p>

</div>

<div class="mt-6 pt-3 border-t border-brand-sand/60 flex items-center justify-between text-\[11px] text-brand-muted font-medium">

<span>Ethical agreement</span>

<span class="text-brand-ochre text-sm font-bold">→</span>

</div>

</div>

<!-- Step 3 -->

<div class="bg-white p-6 rounded-xl border border-brand-sand flex flex-col justify-between shadow-2xs relative">

<div>

<div class="flex items-center justify-between mb-3">

<span class="text-\[11px] font-bold text-brand-ochre uppercase tracking-wider">Step 3</span>

<span class="w-6 h-6 rounded-full bg-brand-sageLight/60 text-brand-ochre flex items-center justify-center font-bold text-xs">3</span>

</div>

<h3 class="font-serif font-bold text-lg text-brand-forestDark mb-2">Share</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;               Supply the group with the information it needs to assess your operation.

&#x20;             </p>

</div>

<div class="mt-6 pt-3 border-t border-brand-sand/60 flex items-center justify-between text-\[11px] text-brand-muted font-medium">

<span>Farm dossier</span>

<span class="text-brand-ochre text-sm font-bold">→</span>

</div>

</div>

<!-- Step 4 -->

<div class="bg-white p-6 rounded-xl border border-brand-sand flex flex-col justify-between shadow-2xs relative">

<div>

<div class="flex items-center justify-between mb-3">

<span class="text-\[11px] font-bold text-brand-ochre uppercase tracking-wider">Step 4</span>

<span class="w-6 h-6 rounded-full bg-brand-sageLight/60 text-brand-ochre flex items-center justify-center font-bold text-xs">4</span>

</div>

<h3 class="font-serif font-bold text-lg text-brand-forestDark mb-2">Prepare</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;               Familiarise yourself with the Basic Production Principles and the SAOSO standard.

&#x20;             </p>

</div>

<div class="mt-6 pt-3 border-t border-brand-sand/60 flex items-center justify-between text-\[11px] text-brand-muted font-medium">

<span>Self review</span>

<span class="text-brand-ochre text-sm font-bold">→</span>

</div>

</div>

<!-- Step 5 -->

<div class="bg-white p-6 rounded-xl border border-brand-sand flex flex-col justify-between shadow-2xs relative">

<div>

<div class="flex items-center justify-between mb-3">

<span class="text-\[11px] font-bold text-brand-ochre uppercase tracking-wider">Step 5</span>

<span class="w-6 h-6 rounded-full bg-brand-sageLight/60 text-brand-ochre flex items-center justify-center font-bold text-xs">5</span>

</div>

<h3 class="font-serif font-bold text-lg text-brand-forestDark mb-2">Visit</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;               A peer assessment team visits the farm and works through the assessment.

&#x20;             </p>

</div>

<div class="mt-6 pt-3 border-t border-brand-sand/60 flex items-center justify-between text-\[11px] text-brand-muted font-medium">

<span>Peer verification</span>

<span class="text-brand-ochre text-sm font-bold">→</span>

</div>

</div>

<!-- Step 6 -->

<div class="bg-white p-6 rounded-xl border border-brand-sand flex flex-col justify-between shadow-2xs relative">

<div>

<div class="flex items-center justify-between mb-3">

<span class="text-\[11px] font-bold text-brand-ochre uppercase tracking-wider">Step 6</span>

<span class="w-6 h-6 rounded-full bg-brand-sageLight/60 text-brand-ochre flex items-center justify-center font-bold text-xs">6</span>

</div>

<h3 class="font-serif font-bold text-lg text-brand-forestDark mb-2">Review</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;               The committee reviews the findings and records a decision.

&#x20;             </p>

</div>

<div class="mt-6 pt-3 border-t border-brand-sand/60 flex items-center justify-between text-\[11px] text-brand-muted font-medium">

<span>Formal record</span>

<span class="text-brand-forest font-bold text-xs">✓ Done</span>

</div>

</div>

</div>

</div>

</section>

<!-- END: HowItWorks -->

<!-- BEGIN: FeesSection -->

<section class="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto" data-purpose="fees-schedule">

<div class="max-w-2xl mb-10">

<span class="text-xs font-bold tracking-widest uppercase text-brand-sage block mb-2">Fees</span>

<h2 class="serif-title text-3xl sm:text-4xl text-brand-forestDark font-normal tracking-tight mb-3">

&#x20;         What membership and assessment cost

&#x20;       </h2>

<p class="text-sm text-brand-muted leading-relaxed">

&#x20;         Fees are set on a cost-recovery basis and approved by the members at the annual general meeting. The assessment fee reflects the scale and commercial intensity of the farm.

&#x20;       </p>

</div>

<!-- Integrated Introductory Highlight Box: Which Band Are You In? -->

<div class="mb-10 bg-brand-creamWarm p-6 sm:p-7 rounded-xl border border-brand-sand shadow-2xs flex flex-col lg:flex-row lg:items-center justify-between gap-6">

<div class="max-w-3xl">

<div class="flex items-center gap-2 mb-2">

<span class="w-2 h-2 rounded-full bg-brand-ochre"></span>

<h3 class="serif-title text-lg sm:text-xl font-bold text-brand-forestDark">Which band are you in?</h3>

</div>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed mb-2">

&#x20;         Turnover is <strong class="text-brand-charcoal font-semibold">self-declared</strong> and subject to peer review. You tell us the band you fall in; we do not estimate it for you. If you are uncertain, ask the administrator and the group will work it out with you before the visit.

&#x20;       </p>

<p class="text-xs text-brand-muted leading-relaxed">

&#x20;         Fees are payable <strong class="text-brand-charcoal font-semibold">before</strong> the farm assessment visit, per the group’s procedures.

&#x20;       </p>

</div>

<div class="flex flex-col sm:flex-row lg:flex-col gap-2.5 shrink-0 min-w-\[220px]">

<a class="text-center py-2.5 px-4 rounded-full text-xs font-semibold text-white bg-brand-ochre hover:bg-brand-ochreDark transition-colors shadow-sm" href="#ask-standard">

&#x20;         Ask about fees

&#x20;       </a>

<a class="text-center py-2.5 px-4 rounded-full text-xs font-semibold text-brand-forest bg-white border border-brand-sand hover:bg-brand-sand/30 transition-colors" href="#contact">

&#x20;         Contact the administrator

&#x20;       </a>

</div>

</div>

<!-- Fee Structure Tables: Side by side modular layout -->

<div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

<!-- Left: Annual Membership -->

<div class="lg:col-span-5 bg-white p-6 sm:p-7 rounded-xl border border-brand-sand shadow-xs">

<h3 class="serif-title text-xl font-bold text-brand-forestDark mb-5">Annual membership</h3>

<div class="space-y-4">

<div class="flex items-center justify-between py-2 border-b border-dashed border-brand-sand/70">

<span class="text-sm text-brand-charcoal font-medium">Farmer \&amp; consumer membership</span>

<span class="text-sm font-bold text-brand-ochreDark">R100</span>

</div>

<div class="flex items-center justify-between py-2 border-b border-dashed border-brand-sand/70">

<div>

<span class="text-sm text-brand-charcoal font-medium block">PGS South Africa membership</span>

<span class="text-xs text-brand-muted">Paid by the group from membership fees</span>

</div>

<span class="text-sm font-bold text-brand-ochreDark">R500</span>

</div>

</div>

<div class="flex gap-2 mt-6">

<span class="inline-flex items-center px-2.5 py-1 rounded-md text-\[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-200">

&#x20;           Approved at the 2025 AGM

&#x20;         </span>

<span class="inline-flex items-center px-2.5 py-1 rounded-md text-\[11px] font-semibold bg-brand-sand/50 text-brand-charcoal">

&#x20;           Per year

&#x20;         </span>

</div>

</div>

<!-- Right: Assessment \& Certification Table -->

<div class="lg:col-span-7 bg-white p-6 sm:p-7 rounded-xl border border-brand-sand shadow-xs">

<h3 class="serif-title text-xl font-bold text-brand-forestDark mb-4">Assessment \&amp; certification</h3>

<div class="overflow-x-auto">

<table class="w-full text-left text-xs" data-purpose="pricing-table">

<thead>

<tr class="border-b border-brand-sand text-brand-muted uppercase text-\[10px] tracking-wider font-semibold">

<th class="py-3 font-semibold" scope="col">Annual Turnover</th>

<th class="py-3 font-semibold text-right" scope="col">Initial</th>

<th class="py-3 font-semibold text-right" scope="col">Renewal</th>

</tr>

</thead>

<tbody class="divide-y divide-brand-sand/50 font-normal">

<tr>

<td class="py-3 text-brand-charcoal">Below R250 000</td>

<td class="py-3 text-right font-medium text-brand-ochreDark">1 500</td>

<td class="py-3 text-right text-brand-muted">900</td>

</tr>

<tr>

<td class="py-3 text-brand-charcoal">R250 001 – R500 000</td>

<td class="py-3 text-right font-medium text-brand-ochreDark">2 500</td>

<td class="py-3 text-right text-brand-muted">2 000</td>

</tr>

<tr>

<td class="py-3 text-brand-charcoal">R500 001 – R1 000 000</td>

<td class="py-3 text-right font-medium text-brand-ochreDark">3 000</td>

<td class="py-3 text-right text-brand-muted">2 500</td>

</tr>

<tr>

<td class="py-3 text-brand-charcoal">R1 000 001 – R2 500 000</td>

<td class="py-3 text-right font-medium text-brand-ochreDark">3 700</td>

<td class="py-3 text-right text-brand-muted">3 200</td>

</tr>

<tr>

<td class="py-3 text-brand-charcoal">R2 500 001 – R5 000 000</td>

<td class="py-3 text-right font-medium text-brand-ochreDark">5 000</td>

<td class="py-3 text-right text-brand-muted">5 000</td>

</tr>

<tr>

<td class="py-3 text-brand-charcoal">Above R5 000 000</td>

<td class="py-3 text-right font-medium text-brand-ochreDark">8 000</td>

<td class="py-3 text-right text-brand-muted">8 000</td>

</tr>

</tbody>

</table>

</div>

<p class="text-\[11px] text-brand-muted mt-5 leading-normal italic">

&#x20;         Fees are per farm assessment visit. Transport for the administrator is charged separately at the AA rate; visits are clustered geographically wherever possible to reduce that cost.

&#x20;       </p>

</div>

</div>

</section>

<!-- END: FeesSection -->

<!-- BEGIN: DocumentsSection -->

<section class="py-20 bg-brand-creamWarm border-y border-brand-sand" data-purpose="downloadable-resources" id="documents">

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

<div class="max-w-3xl mb-12">

<span class="text-xs font-bold tracking-widest uppercase text-brand-sage block mb-2">Documents</span>

<h2 class="serif-title text-3xl sm:text-4xl text-brand-forestDark font-normal tracking-tight mb-3">

&#x20;           Everything you need, in one place

&#x20;         </h2>

<p class="text-sm text-brand-muted leading-relaxed">

&#x20;           The standard, our own procedures, the Basic Production Principles, the certification landscape and the blank checklists. No Drive links, no permission requests — stable addresses you can bookmark and cite.

&#x20;         </p>

</div>

<!-- Organized Tabular Directory List Layout -->

<div class="bg-white rounded-xl border border-brand-sand shadow-xs divide-y divide-brand-sand/60 mb-5 overflow-hidden">

<!-- Doc 1 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">SAOSO Organic Standard v2.1</h4>

<p class="text-\[11px] text-brand-muted">The standard we assess against · 2026</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

<!-- Doc 2 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">Principles, Policies \&amp; Procedures</h4>

<p class="text-\[11px] text-brand-muted">How our own PGS is governed</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

<!-- Doc 3 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">Basic Production Principles</h4>

<p class="text-\[11px] text-brand-muted">Growing the organic sector in South Africa</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

<!-- Doc 4 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">Certification Landscape</h4>

<p class="text-\[11px] text-brand-muted">Seals and recognition in the SA organic sector</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

<!-- Doc 5 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">Farm Visit Preparation List</h4>

<p class="text-\[11px] text-brand-muted">What to have ready before the visit</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

<!-- Doc 6 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">Checklist — Crops</h4>

<p class="text-\[11px] text-brand-muted">Blank participant checklist</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

<!-- Doc 7 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">Checklist — Crops \&amp; Animals</h4>

<p class="text-\[11px] text-brand-muted">Blank participant checklist</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

<!-- Doc 8 -->

<div class="p-4 sm:p-5 flex items-center justify-between gap-4 hover:bg-brand-cream/50 transition-colors">

<div class="flex items-center gap-3.5 min-w-0">

<span class="text-\[10px] font-bold text-amber-900 bg-amber-100/70 border border-amber-200 px-2.5 py-1 rounded tracking-wider shrink-0">PDF</span>

<div class="min-w-0">

<h4 class="text-xs sm:text-sm font-bold text-brand-charcoal truncate">Checklist — Seed Production</h4>

<p class="text-\[11px] text-brand-muted">Blank participant checklist</p>

</div>

</div>

<a class="inline-flex items-center px-3.5 py-1.5 rounded-full text-xs font-semibold text-brand-ochreDark hover:text-white bg-brand-sand/40 hover:bg-brand-ochre transition-colors shrink-0" href="#">Download</a>

</div>

</div>

<!-- Archival Record Row -->

<div class="bg-amber-50/80 border border-amber-200 rounded-lg p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">

<div class="flex items-start sm:items-center gap-3">

<span class="w-6 h-6 rounded bg-amber-200/80 text-amber-900 flex items-center justify-center font-bold text-\[10px] shrink-0">

<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewbox="0 0 24 24">

<path d="M12 15v2m0 0v2m0-2h2m-2 0H8m13-5a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"></path>

</svg>

</span>

<div>

<span class="font-bold text-brand-charcoal block">Farm visit reports \&amp; application dossiers</span>

<span class="text-brand-muted text-\[11px]">Historical records containing farmer personal data. Never published on a public address.</span>

</div>

</div>

<a class="font-semibold text-brand-forestDark hover:underline shrink-0 text-left sm:text-right" href="#contact">

&#x20;           Request access

&#x20;         </a>

</div>

</div>

</section>

<!-- END: DocumentsSection -->

<!-- BEGIN: AskTheStandardSection -->

<section class="py-24 bg-brand-forest text-brand-cream" data-purpose="chat-qa-showcase" id="ask-standard">

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

<!-- Heading -->

<div class="max-w-3xl mb-14">

<span class="text-xs font-bold tracking-widest uppercase text-amber-300 block mb-2">Ask The Standard</span>

<h2 class="serif-title text-3xl sm:text-4xl lg:text-5xl font-normal text-white tracking-tight mb-4">

&#x20;           A straight answer, or none at all

&#x20;         </h2>

<p class="text-sm sm:text-base text-brand-cream/80 leading-relaxed">

&#x20;           Ask a question about the standard, our procedures or the certification landscape. Answers are drawn only from the documents above, and every answer cites the passage it came from. If the documents do not cover your question, we will say so rather than guess.

&#x20;         </p>

</div>

<!-- Interactive Comparison Cards -->

<div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">

<!-- Mockup 1: When Answered -->

<div>

<div class="text-\[11px] font-bold tracking-wider text-amber-300 uppercase mb-3 flex items-center justify-between">

<span>When the standard answers</span>

<span class="text-\[10px] text-amber-300 font-mono">Case A</span>

</div>

<!-- Terminal / Chat Window -->

<div class="bg-brand-forestDark rounded-xl border border-white/10 overflow-hidden shadow-2xl">

<!-- Top bar -->

<div class="bg-\[#1C2317] px-4 py-3 border-b border-white/5 flex items-center justify-between">

<div class="flex items-center gap-2">

<span class="w-2 h-2 rounded-full bg-amber-400"></span>

<span class="text-xs font-medium text-brand-cream/90">Ask Outeniqua PGS</span>

</div>

<span class="text-\[10px] font-bold text-amber-300 uppercase tracking-widest bg-amber-950/70 border border-amber-800/80 px-2 py-0.5 rounded">Answered</span>

</div>

<!-- Chat Body -->

<div class="p-5 space-y-4">

<!-- User Question -->

<div class="flex justify-end">

<div class="bg-brand-moss/80 border border-white/10 rounded-2xl rounded-tr-none px-4 py-2.5 max-w-\[85%] text-xs text-white">

&#x20;                   What is the membership fee for a farmer?

&#x20;                 </div>

</div>

<!-- Bot Response -->

<div class="flex justify-start">

<div class="bg-brand-forest/70 border border-white/10 rounded-2xl rounded-tl-none p-4 max-w-\[90%] text-xs text-brand-cream/90 space-y-3">

<p class="leading-relaxed">

&#x20;                     Annual farmer and consumer membership is <strong class="text-white font-semibold">R100</strong>. On top of that, the group pays an annual PGS South Africa membership fee of <strong class="text-white font-semibold">R500</strong>, which is funded from the membership fees collected.

&#x20;                   </p>

<!-- Citations -->

<div class="flex flex-wrap gap-2 pt-2">

<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-brand-forestDark text-\[10px] font-mono text-amber-200 border border-amber-500/25">

&#x20;                       📄 OPP §2.1

&#x20;                     </span>

<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-brand-forestDark text-\[10px] font-mono text-amber-200 border border-amber-500/25">

&#x20;                       📄 Fees

&#x20;                     </span>

</div>

</div>

</div>

</div>

<!-- Fake Input Bar -->

<div class="p-3 bg-\[#1C2317] border-t border-white/5 flex items-center justify-between">

<span class="text-xs text-brand-cream/40 pl-2">Ask about the standard...</span>

<span class="w-7 h-7 rounded-full bg-brand-moss/80 flex items-center justify-center text-white/60 text-xs">

&#x20;                 →

&#x20;               </span>

</div>

</div>

</div>

<!-- Mockup 2: When Refused Gracefully -->

<div>

<div class="text-\[11px] font-bold tracking-wider text-amber-300/80 uppercase mb-3 flex items-center justify-between">

<span>When it does not</span>

<span class="text-\[10px] text-amber-300 font-mono">Case B</span>

</div>

<!-- Terminal / Chat Window -->

<div class="bg-brand-forestDark rounded-xl border border-white/10 overflow-hidden shadow-2xl">

<!-- Top bar -->

<div class="bg-\[#1C2317] px-4 py-3 border-b border-white/5 flex items-center justify-between">

<div class="flex items-center gap-2">

<span class="w-2 h-2 rounded-full bg-amber-500"></span>

<span class="text-xs font-medium text-brand-cream/90">Ask Outeniqua PGS</span>

</div>

<span class="text-\[10px] font-bold text-amber-200 uppercase tracking-widest bg-amber-950/70 border border-amber-800/80 px-2 py-0.5 rounded">Refusal</span>

</div>

<!-- Chat Body -->

<div class="p-5 space-y-4">

<!-- User Question -->

<div class="flex justify-end">

<div class="bg-brand-moss/80 border border-white/10 rounded-2xl rounded-tr-none px-4 py-2.5 max-w-\[85%] text-xs text-white">

&#x20;                   Do I need EU organic certification to export to Germany?

&#x20;                 </div>

</div>

<!-- Bot Response -->

<div class="flex justify-start">

<div class="bg-\[#2B2319]/90 border border-amber-900/40 rounded-2xl rounded-tl-none p-4 max-w-\[90%] text-xs text-amber-100/90 space-y-3">

<p class="leading-relaxed">

&#x20;                     I could not find this in the documents this group publishes. I can answer from the SAOSO Organic Standard, our Principles, Policies and Procedures, the Basic Production Principles, and the SA Organic Certification Landscape — and none of them covers EU market access. Please ask the administrator.

&#x20;                   </p>

<div class="pt-1">

<a class="inline-flex items-center text-\[11px] font-semibold text-amber-200 hover:text-white underline" href="#contact">

&#x20;                       → Send to the administrator

&#x20;                     </a>

</div>

</div>

</div>

</div>

<!-- Fake Input Bar -->

<div class="p-3 bg-\[#1C2317] border-t border-white/5 flex items-center justify-between">

<span class="text-xs text-brand-cream/40 pl-2">Ask about the standard...</span>

<span class="w-7 h-7 rounded-full bg-brand-moss/80 flex items-center justify-center text-white/60 text-xs">

&#x20;                 →

&#x20;               </span>

</div>

</div>

</div>

</div>

</div>

</section>

<!-- END: AskTheStandardSection -->

<!-- BEGIN: MembersAdvisory -->

<section class="py-20 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto" data-purpose="members-directory" id="members">

<div class="max-w-2xl mb-8">

<span class="text-xs font-bold tracking-widest uppercase text-brand-sage block mb-2">Members</span>

<h2 class="serif-title text-3xl sm:text-4xl text-brand-forestDark font-normal tracking-tight">

&#x20;         Who is in the group

&#x20;       </h2>

</div>

<!-- Advisory Box -->

<div class="bg-white border border-brand-sand rounded-xl p-6 sm:p-8 flex items-start gap-5 shadow-xs">

<div class="w-9 h-9 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center shrink-0 mt-0.5">

<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewbox="0 0 24 24">

<path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" stroke-linecap="round" stroke-linejoin="round"></path>

</svg>

</div>

<div class="space-y-3">

<h3 class="serif-title text-lg font-bold text-brand-forestDark">Membership is not certification</h3>

<p class="text-xs sm:text-sm text-brand-muted leading-relaxed">

&#x20;           The people and farms listed here are members of the Outeniqua Natural and Organic PGS group. Membership of the group is <strong class="text-brand-charcoal font-semibold">not</strong> a certification, and does not by itself mean that a farm is certified organic. A certification decision is a separate judgement made by the group’s certification committee against the SAOSO standard, and is recorded as such. Please do not read this list as a claim about any farm’s organic status.

&#x20;         </p>

<p class="text-xs text-brand-muted">

&#x20;           The member list is being prepared for publication. <span class="font-mono text-\[11px] bg-brand-creamWarm px-2 py-0.5 rounded border border-brand-sand">names \&amp; consent — MAP 2</span>

</p>

</div>

</div>

</section>

<!-- END: MembersAdvisory -->

</main>

<!-- BEGIN: SiteFooter -->

<footer class="bg-brand-forestDeep text-brand-cream pt-16 pb-12 border-t border-brand-forest" data-purpose="site-footer" id="contact">

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

<!-- Top 4 Columns -->

<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-10 pb-14 border-b border-white/10">

<!-- Col 1: Brand Info -->

<div class="lg:col-span-5 space-y-3">

<h4 class="serif-title text-lg font-bold text-white tracking-tight">Outeniqua Natural \&amp; Organic PGS</h4>

<p class="text-xs text-brand-cream/70 leading-relaxed max-w-sm">

&#x20;           A participatory guarantee group of farmer and consumer members in the Western Cape, assessing organic practice against the SAOSO standard.

&#x20;         </p>

</div>

<!-- Col 2: The Group -->

<div class="lg:col-span-2 space-y-3">

<h5 class="text-\[11px] font-bold uppercase tracking-wider text-amber-300">The Group</h5>

<ul class="space-y-2 text-xs text-brand-cream/80">

<li><a class="hover:text-white transition-colors" href="#organics">Organics</a></li>

<li><a class="hover:text-white transition-colors" href="#how-it-works">How it works</a></li>

<li><a class="hover:text-white transition-colors" href="#members">Members</a></li>

<li><a class="hover:text-white transition-colors" href="#organics">Fees</a></li>

</ul>

</div>

<!-- Col 3: Documents -->

<div class="lg:col-span-2 space-y-3">

<h5 class="text-\[11px] font-bold uppercase tracking-wider text-amber-300">Documents</h5>

<ul class="space-y-2 text-xs text-brand-cream/80">

<li><a class="hover:text-white transition-colors" href="#documents">SAOSO Standard v2.1</a></li>

<li><a class="hover:text-white transition-colors" href="#documents">Our procedures</a></li>

<li><a class="hover:text-white transition-colors" href="#documents">Basic Production Principles</a></li>

<li><a class="hover:text-white transition-colors" href="#documents">Blank checklists</a></li>

</ul>

</div>

<!-- Col 4: Contact -->

<div class="lg:col-span-3 space-y-3">

<h5 class="text-\[11px] font-bold uppercase tracking-wider text-amber-300">Contact</h5>

<p class="text-xs text-brand-cream/80 leading-relaxed">

&#x20;           Outeniqua, Western Cape

&#x20;         </p>

<div class="flex gap-2 pt-1 font-mono text-\[10px]">

<span class="px-2 py-0.5 rounded bg-brand-forest text-amber-300 border border-white/10">email</span>

<span class="px-2 py-0.5 rounded bg-brand-forest text-amber-300 border border-white/10">phone</span>

</div>

<div class="pt-2">

<a class="text-xs text-amber-300 hover:underline" href="#ask-standard">

&#x20;             Ask the standard →

&#x20;           </a>

</div>

</div>

</div>

<!-- Bottom Bar -->

<div class="pt-8 flex flex-col sm:flex-row items-center justify-between text-\[11px] text-brand-cream/50 gap-4">

<div>

&#x20;         © 2026 Outeniqua Natural \&amp; Organic PGS.

&#x20;       </div>

<div class="text-center sm:text-right">

&#x20;         Membership is not certification. No certification status is published on this page.

&#x20;       </div>

<div class="inline-flex items-center p-0.5 rounded-full bg-white/5 border border-white/10 text-\[10px]">

<span class="px-2 py-0.5 text-brand-cream/60">BASE</span>

<span class="px-2 py-0.5 text-brand-cream/60">Cool</span>

<span class="px-2 py-0.5 rounded-full bg-white/20 text-white font-medium">Warm</span>

</div>

</div>

</div>

</footer>

<!-- END: SiteFooter -->

</body></html>

