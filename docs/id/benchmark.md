# Industrial design benchmark and directions (v0.1)

Scope: design language, CMF (colour, material, finish) and manufacturability for the Ø95 × 216 mm stereo capsule (`docs/requirements.md`, `docs/mech_envelope.md`). Acoustic and packaging limits come from the physics-constraints work running in parallel. Any change to the silhouette or a driver opening below must be checked against those limits before CAD.

Citations are numbered `[n]` and listed in §7. Lines marked **(obs.)** are visual observations from the linked product pages or photos, not published specs. Lines marked **(synthesis)** are our own design judgement drawn from the benchmark.

---

## 0. Why the current concept reads "DIY"

From `mech/concept/view_iso.png` and `view_front.png` (obs.):

- **It reads as a face.** With the grille off, the front shows two high tweeter "eyes" and two large woofer "cheeks", all with the same black fill and the same weight. Even under a translucent grille the four circles dominate.
- **There is no hierarchy.** It is a uniform tube with equal-weight features. Nothing reads as the front, the top or the hero detail.
- **The controls look bolted on.** The display, the knob and the button strip each sit on their own flat pad with a visible step on the curve, at three unrelated X positions. The knob is a 13 mm-tall "chimney" near one end.
- **The colours are unrelated.** Orange knob and plungers, a blue lens and grey shells share no CMF logic.
- **The PR frames are square on a round cap.** The squircle PR frame sits on a round end cap with no transition, and the end caps carry no design intent.
- **The proportions are stubby.** L/D ≈ 2.3 (216/95), against ≈ 2.6 for the Flip 7 (182.5/70 [1]) and ≈ 3.1 for the Beats Pill (219/70 [18]). Our volume is **Charge-class**, not Flip-class: the Charge 6 is 229 × 99 × 94 mm [4]. Design it as a Charge-sized object.

---

## 1. Benchmark

### 1a. Form, size, carry

| Product | Silhouette / cross-section | Size (mm) / mass | Carry | Feet / stability |
|---|---|---|---|---|
| **JBL Flip 7** | Horizontal cylinder | 182.5 × 69.5 × 71.5, 0.56 kg [1] | Fabric strap loop on one end (obs. [1]) | Moulded flat underside (obs.); four protruding rubber bumpers at the PR ends [2] |
| **JBL Flip 6** | Same family, "more bulbous" than the Flip 5 [19b] | 178 × 68 × 72, 0.55 kg [19] | Strap loop (obs.) | Rubberised end caps [19c] |
| **JBL Charge 6** | Larger horizontal cylinder | 229 × 99 × 94, ~0.96–0.99 kg [4][4b] | Detachable handle [5] | Integrated foot (obs.) |
| **JBL Charge 5** (PR reference) | Cylinder, open ends | — | — | Silicone side bumpers guard the PRs [6]; open ends let you see the PRs move [6b] |
| **UE Boom 4** | Vertical cylinder | 73 × 73 × 184, 620 g [7] | Loop at the top (obs. [7]) | Stands on its end; USB-C on the bottom [7b] |
| **Bose SoundLink Flex (2nd Gen)** | Flat lozenge, rounded edges | 201 × 52 × 90, 0.59 kg [8] | Nylon strap [8b] | Stands up or lies flat (obs.) |
| **Bose SoundLink Max** | Wide rounded box | 265 × 105 × 120, 2.13 kg [9][9b] | Rope handle, detachable, sold as an accessory [9d] | Rubberised body [9b][9c] |
| **B&O Beosound A1 2nd Gen** | Disc ("hockey puck") | 133 × 46 × 133, 558 g [10c] | Leather wrist strap with a tubular slider [10] | Leather base [10b] |
| **B&O Beosound Explore** | Short vertical cylinder | 81 × 124 × 81, 631 g (637 g with carabiner) [11] | Carabiner [11b] | Stands on its end |
| **Marshall Emberton III** | Rounded rectangle, horizontal | 160 × 68 × 77, 0.67 kg [12] | None (obs.) | Silicone-wrapped body (obs. [12]) |
| **Marshall Middleton** | Larger rounded box | 230 × 109 × 95, 1.8 kg [13] | Strap (obs. [13]) | "Rubberised casing" [13b] |
| **Sonos Roam 2** | Triangular prism, rounded | 168 × 62 × 60, 0.43 kg [14] | None | Lies on a flat or stands up (obs. [14b]) |
| **Anker Soundcore Motion 300** | Flat rectangular box | 199 × 92 × 50, ~0.8 kg [15] | Detachable strap [15b] | Silicone edges [15b] |
| **Teenage Engineering OB-4** | Thin slab with a handle | 232.5 × 284 × 57.5 (incl. handle), 1.7 kg [16] | Handle that doubles as a stand [16] | Handle-stand [16] |
| **Devialet Mania** | Near-sphere | 193 × 176 × 139, 2.3 kg [17] | Integrated handle, criticised as two-finger-only [17b][17c] | Sits on its base |
| **Beats Pill (2024)** | Long slim capsule | 219 × 71 × 70, 681 g [18] | Removable lanyard [18b] | Soft-grip backing [18b] |
| **This project (concept)** | Cylinder Ø95, 33 mm bottom flat | 216 × 95 × 92 | None yet | Flat only |

### 1b. Expression and CMF

| Product | PR / grille expression | Controls / display | CMF | Reads premium because / cheap because |
|---|---|---|---|---|
| **JBL Flip 7 / 6** | Exposed PRs on both ends, framed by rubber bumpers [2] | Buttons on top (obs.) | Recycled plastic + fabric grille [3] | + one-piece fabric wrap and tight bumpers; − large logo, rubbery parts (synthesis) |
| **JBL Charge 6** | Fabric wrap over the woofer; ends open to the PRs [4b][6b] | Physical buttons on top, embossed logo [4b] | Woven fabric wrap, rubber [4c] | + rugged honesty; − toy-like at desk scale (synthesis) |
| **UE Boom 4** | 360° fabric | Very large +/− on the fabric (obs. [7]) | "High performance fabric", ≥ 52 % recycled plastic [7] | + colour confidence; − giant icons belong to UE's trade dress, avoid |
| **Bose SL Flex 2** | Powder-coated steel grille on the face [8c] | Button row on top (obs.) | Aluminium, fabric, nylon, plastic, silicone, steel [8] | + metal face against a soft-touch body [8c] |
| **Bose SL Max** | Front grille, rubber body | Top buttons (obs.) | Plastic, rubber, silicone [9c]; the rubber finish collects dust [9b] | + the rope handle as a colour accent [9d]; − dust pick-up [9b] |
| **B&O A1 2nd Gen** | Drilled holes in an aluminium top [10b] | Minimal buttons on the edge (obs.) | Pearl-blasted anodised aluminium, leather, polymer [10c] | + real metal, real leather, very few visible parts |
| **B&O Explore** | Aluminium shell with grille (obs. [11b]) | Top buttons (obs.) | Fabric, plastic, Type II anodised aluminium [11c] | + one metal extrusion-like shell, integrated carabiner [11b] |
| **Marshall Emberton III** | Metal grilles front and back [12b] | Brass multi-directional knob on top [12b] | Silicone wrap (obs. [12]), metal grilles, brass knob [12b] | + one metal "jewel" control; − script logo/amp styling is trade dress, avoid |
| **Marshall Middleton** | "Rock-solid grille with gold accents" [13b] | Brass knob in the centre of the top [13c] | Rubberised casing, metal grille [13b] | + metal accents; − heavy [13d] |
| **Sonos Roam 2** | Perforated grille wrapped around the prism (obs. [14b]) | Separate power/BT buttons, refreshed monochrome logo [14b] | Matte plastic, monochrome (obs.) | + monochrome, tonal logo, tight radii |
| **Anker Motion 300** | Metal grille [15b] | Top buttons (obs.) | Metal grille, silicone edges [15b] | + metal face at a low price |
| **TE OB-4** | Front grille on a slab (obs. [16b]) | Handle as stand; radio-like controls [16][16c] | Glass-fibre-reinforced PC, milled aluminium, "gel-dampened" handle [16] | + a single bold colour, honest machined parts; Braun T52 lineage [16c] |
| **Devialet Mania** | Visible push-push woofers, woven skin over an exoskeleton [17d] | Minimal (obs.) | Acoustic cloth "flawlessly applied" [17e]; special editions with gold accents [17d] | + continuous form, fabric fit; − handle ergonomics [17c] |
| **Beats Pill** | Full-face grille; racetrack drivers [18] | Few buttons; criticised as "too few buttons" [18c] | Matte plastic, lanyard [18b] | + long slim proportion |

### 1c. Takeaways (synthesis)

1. **One metal touchpoint carries the whole product.** Marshall (brass knob [12b]), B&O (aluminium [10c][11c]) and Bose Flex (steel face [8c]) each use a real material exactly where you look or touch.
2. **The grille is a single, continuous surface with hidden edges.** Fabric wraps (JBL, UE, Devialet) and metal faces (Bose Flex, Anker, B&O) never show a raw cut edge or a visible clip.
3. **Exposed PRs read best when framed.** JBL frames its PRs with bumpers [2][6]. A plain flange screwed onto a flat cap (our concept) reads like a component, not a feature.
4. **The best products show very few visible parts and seams.** Sonos and B&O keep it monochrome or tonal, with logos in the same colour as the body [14b].
5. **The carry feature is part of the identity:** rope (Bose [9d]), leather (B&O [10]), carabiner (Explore [11b]), handle-stand (OB-4 [16]). Don't bolt on a generic strap.
6. **Our size is Charge-class** [4]. Desk and event presence comes from proportion and detail, not from shrinking.

---

## 2. Patterns: premium vs DIY (horizontal speaker with exposed PRs)

| Reads premium | Reads DIY / cheap |
|---|---|
| One continuous grille wrap with edges tucked into a groove or under a trim ring | Flat sheet with visible cut edges, tabs, screws or VHB showing |
| **Fine** perforation, tight pitch, one hole size everywhere | Coarse holes, or two hole patterns that don't line up |
| PR framed by a concentric bezel or "lens ring" that turns the squircle frame round | PR flange screwed onto a flat cap, screw heads visible |
| Controls gathered on one axis ("instrument line") on one flat land | Each control on its own pad, scattered along the length |
| Display behind a flush, dark ("dead-front") lens that vanishes when off | Bezel-mounted TFT with visible black border on a light body |
| Knob low (≤ 8 mm proud), large diameter, knurled metal, set in a recess | Tall narrow printed knob sticking up |
| 2–3 materials, 2 colours max plus one metal; tonal logo | Many unrelated colours (current orange + blue + grey) |
| Split lines that are deliberate shadow lines or reveals [F9] | Butt joints with steps, gaps, misalignment |
| Layer lines turned into an intended texture: rings, fuzzy skin, textured plate [F1][F8][F10] | Accidental layer lines, Z-seam zipper, stringing on show faces |
| No visible fasteners on front or top: axial screws hidden under the PR bezel or a foot | Countersunk screws on show faces |
| A continuous foot rail or a seamless flat with a soft insert | Four stick-on dots on a curved bottom |
| Two of the four drivers hidden (tweeters under the grille) or treated as one graphic | Four equal black circles = "face" |

---

## 3. Making FDM look premium on the Adventurer 5M Pro

The printer has a 220 × 220 × 220 mm envelope, a 280 °C nozzle and an enclosure, and runs PETG, ASA and TPU [F16]. Flashforge's Orca fork is now "Flash Studio"; stock OrcaSlicer ≥ 1.8 also supports the printer [F16c].

Current plan (`mech_envelope.md §3`):

- **Shells print standing on end.** The layer lines form **rings around the capsule axis**, and the Z-seam runs as an axial line.
- **End caps print outer face down.** That face takes whatever plate texture is used.

| Technique | How (settings to start from) | PETG / ASA | Where on this product | Sources |
|---|---|---|---|---|
| **Orientation as texture** | Accept the circumferential rings and make them read "turned", or hide them with fuzzy skin or matte filament | Both | Shell exterior | [F10] |
| **Seam placement** | Seam = Aligned/Rear, then **paint the seam into the rear split line or a modelled reveal groove**. Note the painted seam lands only approximately where painted [F4]. Orca **scarf seams** (Contour; 20 mm length, 10 steps defaults) soften the zipper on curves but don't remove it [F5] | Both | Shells: run the seam down the rear split (φ ≈ ±120°) | [F4][F5] |
| **Fuzzy skin** | Outer walls only. Subtle matte: ~0.1–0.15 mm thickness, 0.1–0.3 mm point distance [F3]. Common default 0.3 / 0.8 mm (coarser) [F1]. Paint it on per area, so seams, lands and mating faces stay smooth [F1] | Both | Rear/bottom shell, end-cap rims; **not** on grille seats, gasket faces or lens lands | [F1][F2][F3] |
| **Textured PEI plate** | The texture transfers to the bottom face [F8]. Rough bottoms are a con elsewhere [F8c], a feature here. Clean with IPA, not acetone [F8b] | Both | **End caps (outer face down): a free factory-like texture** behind the PR bezel; knob caps; badge plates | [F8][F8b][F8c] |
| **Ironing** | Top-most surface only; monotonic infill; slow (~25 mm/s) [F6]. PETG irons well but builds up on the nozzle [F6b] | PETG risky, ASA OK | Few upward-facing show faces in the on-end orientation; use for flat badges or UI-land inserts printed flat | [F6][F6b] |
| **Variable layer height** | Auto + Smooth, repeated; keep thin layers where curvature in Z is high [F7]. Unsmoothed steps defeat the purpose [F7b] | Both | Chamfers and radii at the shell ends, tweeter bosses, knob skirt | [F7][F7b] |
| **Matte filament** | Matte PETG hides layer lines (vendor claims) [F11] | PETG | All show parts | [F11] |
| **Colour choice** | Light colours diffuse light and hide lines; avoid glossy black on show faces [F10b] | Both | Main shell | [F10b] |
| **Two-tone, separate parts** | Different filament per part, joined at a shadow line | Both | Recommended way to get two-tone | [F9] |
| **Two-tone, filament change at height** | Layer-slider "change filament"/pause in Orca [F12]. Expect a blob ("zit") at the change [F12b]. Put the change on a modelled groove so it hides there | Both | With shells on end, a change at Z makes **colour bands at the capsule ends**: cheap two-tone without extra parts | [F12][F12b][F12c] |
| **Shadow line / reveal** | Overlap lip ~1.6 mm, **0.4 mm chamfer** on both outside edges, so a small mismatch shows as a line, not a step [F9b] | Both | Front/rear shell split, cap-to-shell joint, grille edge | [F9][F9b] |
| **Sand + filler primer + paint** | Wet-sand from ~400 grit; filler primer for minor lines, spot putty for gaps; re-spray and sand P400 [F13b][F13c]. **PETG needs an adhesion primer** [F13]. Match primer and paint brands [F13e]. Adhesion test data [F13d] | PETG: OK with adhesion primer. ASA: sands easier and also takes acetone | Hero/demo unit only; too labour-heavy for v1 iterations | [F13]–[F13e] |
| **Acetone vapour (ASA only)** | Short exposures (1–3 min heated, or a cold chamber); low humidity, else the finish clouds; loses fine detail and dimensions [F14][F14b] | **ASA only** | Not for mating faces or threads; possible on end caps or knob | [F14][F14b][F14c] |
| **ASA vs PETG** | ASA resists UV fade and cracking better than PETG [F15] | — | PETG for v1 (per `mech_envelope.md`), ASA for the show unit if it lives near windows or outdoors | [F15] |
| **TPU 95A parts** | AD5M Pro supports TPU 95A, 0.6 mm nozzle recommended [F16b] | — | PR guard rings, foot rail, knob grip band, strap lugs | [F16b][H13] |
| **Heat-set inserts** | Iron at print temperature + 10–20 °C [F17b]. McMaster M3 example: Ø4 mm hole, ≥ 6.5 mm wall [F17] (matches the M3 × 5.7, Ø4.0 plan) | Both | All screws, axial only, hidden | [F17][F17b] |

**Non-printed premium materials (integration notes):**

- **Perforated aluminium wrap.** Already planned: 0.8 mm, rolled to R48.3.
  - Hide all four edges. The long edges go into a 1 mm groove under a shadow-line lip, and the short edges go under the end-cap bezel ring.
  - Don't let tabs show.
  - Deburr and give it one directional Scotch-Brite pass along the axis.
- **Expanded aluminium.** More rigid than perforated sheet [H3]. It looks industrial/"event", not desk-premium.
- **Fabric.** The capsule is a single-curvature surface, so cloth wraps it without darts.
  - Parts Express grey/black cloth is "virtually 100 % acoustically transparent" open-weave polyester [H4].
  - Mellotone is about twice as thick and passes ASTM E-84 Class A [H4c].
  - Terminate the cloth in a printed groove with a pressed-in retaining strip.
- **Knurled aluminium knob.** See §4. This is the single best upgrade per dollar (synthesis).
- **Silicone/TPU foot and bumpers.** A continuous rail in a groove beats stick-on dots.
- **Leather, paracord or rope strap.** Anchor it with a hidden printed lug or a Peak Design-style anchor [H10].
- **Magnets.** Hidden retention for a removable grille or strap, behind ≥ 1 mm skin.

---

## 4. Hardware shopping list (elevating parts)

Verify each part number on the live page before ordering: McMaster tables came back fragmented in search.

| Item | Spec / option | Source / part | Use | Notes |
|---|---|---|---|---|
| **Perforated Al, fine** | 0.032" (0.81 mm) 3003, Ø1/16" (1.6 mm) holes on 1/8" staggered centres, **23 % open** | McMaster perforated Al [H1]; Zoro 36 × 40" equivalent [H2b] | Most premium look (fine texture) | **Low open area: needs an acoustic check** by the physics agent before use over the woofers or tweeters |
| **Perforated Al, mid** | 0.032" 3003, Ø1/8" (3.2 mm) on 3/16" centres, **40 % open**; also 6061 at 40 % or 51 % [H1] | McMaster [H1] | Balanced look vs open area | 6061 is harder and stiffer to roll [H1] |
| **Perforated Al, open** | 0.032" 3003, Ø3/16" on 1/4" centres, **51 % open**, ~$88 per 36 × 40" sheet | Zoro [H2] | Highest open area with round holes | Coarser, more "industrial" |
| **Expanded Al (flattened)** | 1100/3003, flattened diamond | McMaster [H3] | Event/tough direction | More rigid than perforated [H3] |
| **Grille cloth** | PE 260-337 grey / 260-335 black, 70" wide, ~$10 per yard; Mellotone 260-332 premium stretch | Parts Express [H4][H4b][H4c] | Knit/soft direction | Standard cloth is **not flame-retardant** [H4b] |
| **Knob, 20 mm** | Anodised Al, 6 mm bore, set screw (2 mm hex), fits T18 knurled, round or D shafts; 12.5 mm tall; $2.95; black, silver, gold and other colours | Adafruit 5527 [H5] | Low-cost metal knob | Fits the EC11 knurled shaft |
| **Knob, 25.6 mm** | Same Sky **SAK-006**, knurled Al, 6 × 4.5 mm D-bore, Ø25.6 | Mouser, Same Sky aluminium knobs [H6] | **Matches the planned Ø26 knob** | Needs a **D-shaft** encoder variant. Mouser shows high MOQs on neighbouring parts; check Digi-Key or the distributor |
| **Knob, industrial** | Knurled anodised Al set-screw knobs, 6 mm-bore filter | McMaster set-screw knobs [H7] | Alternative | Pick the part from the filter |
| **Feet, dots** | 3M Bumpon **SJ5302**, Ø7.9 × 2.2 mm clear polyurethane hemispheres | Digi-Key / 3M [H8][H8b] | Minimal, invisible feet | Only on a flat land |
| **Feet, rail** | Silicone O-ring cord stock (round), pressed into a printed groove | McMaster [H9b] | Continuous foot rail along the bottom flat | Ordinary adhesives don't bond silicone well; retain it mechanically [H9b] |
| **Bumpers** | Adhesive-back bumpers, many materials and heights | McMaster [H9] | PR guard and cap protection | — |
| **Strap anchors** | Peak Design Anchor Links: Ø17 mm anchor disc, ≤ 12 mm strap, >200 lb claimed | REI / Adorama [H10][H10b] | Quick-detach strap or rope | Lug printed into the end-cap rim |
| **Webbing hardware** | Webbing mounting plates for 3/4" webbing; webbing | McMaster [H11][H11b] | Fixed carry strap | — |
| **Magnets** | N52 neodymium discs, e.g. 5862K116 (1/4" × 1/4"); 1/16"-thick discs in the same family | McMaster [H12][H12b] | Hidden grille or strap retention | Ask the physics agent for a minimum distance from the driver motors; confirm the part number |
| **Heat-set inserts** | M3 brass, Ø4 mm hole | McMaster [F17] | All fasteners | Already in plan |
| **Filament** | Matte PETG (Bambu, Fiberlogy, Spectrum) [F11]; TPU 95A [H13]; ASA for the show unit [F15] | — | All printed parts | — |

---

## 5. Original ID directions

All five keep the decided acoustic architecture: two front woofers 66 mm apart, tweeters at 40° on the shoulders, PRs on the end caps, top UI. All five take principles from §1–2, not any product's shapes, logos or signature features. **Directions A and D change the cross-section and need the constraints check.**

### A. "LATHE": the turned capsule *(lowest risk, closest to current geometry)*

A precision-instrument cylinder that leans into the print orientation. The circumferential layer lines become an intended fine "turned" ring texture: matte filament, fine layers, no fuzzy skin. That contrasts with one perforated-aluminium wrap across the front 200°.

- **PRs:** each end cap gets a stepped **lens-bezel ring**, three concentric steps printed face-down on textured PEI. It turns the squircle PR frame into a round, camera-lens-like detail and hides the 4 axial screws under the bezel.
- **Top:** a single flat land milled into the top, running ~150 mm, carries the instrument line in order: buttons, recessed power, display, knob.
- **Display:** flush behind a smoked lens.
- **Knob:** the Ø25.6 knurled aluminium knob (SAK-006), sunk so only ~6 mm stands proud.

```
 end view            front view
   ___               ┌──────────────────────────────────────┐ ← flat top land
  /   \  ◄ grille    │▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│
 | (◎) |    wraps    ◎▒▒ perforated Al (tweeters under it) ▒▒◎  ◎ = lens-bezel PR
  \___/   front 200° │▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒│
   ▔▔▔ foot rail     └══════════════════════════════════════┘ ← silicone rail
```

- **CMF:** graphite or "bone" matte PETG body; natural brushed aluminium grille and knob; end-cap bezels in the body colour with a textured-plate finish; tonal debossed logo on one cap.
- **Printability:** no geometry change. The reveal groove sits at the existing split. Paint the seam into the rear split. Shells print on end as planned.
- **Tweeters:** hide them under the grille rather than in Ø38 clearance holes. This removes the "face" read (acoustic check needed).
- **Why it fits a desk/event showpiece:** it reads as a machined instrument, and the lens-bezel PRs that visibly pump at the ends become the "watch me" detail.

### B. "DECK": two-tone instrument spine

The capsule splits visually into a dark acoustic "hull" (front + bottom) and a light **top deck**: a separate printed part in a contrasting colour that runs the full length and carries the whole UI. The deck sits proud by 0.5 mm behind a continuous shadow line, like a control surface set into a chassis.

- **PRs:** dark TPU guard rings flush with the deck colour band.
- **Display:** centred in the deck under a dark lens, so it reads as a "window" into the hull colour.
- **Knob:** on the deck, with a printed arc of tick marks around it.
- **Tweeters:** sit exactly at the colour break and read as part of the band, not as eyes.

```
 end view                front view
   _____  ◄ light deck   ┌─────────────[ ● ○ ○  (◉)  ⊚ ]──────────┐ ← deck
  /─────\ ◄ shadow line  ├──────────────────────────────────────┤
 |  ▓▓▓  | dark hull     ║▓▓▓▓▓ dark perforated / fuzzy hull ▓▓▓▓▓║
  \_____/                └──────────────────────────────────────┘
```

- **CMF:** hull in charcoal matte PETG with fuzzy skin and black (or rattle-can satin black) perforated Al; deck in off-white or one strong accent (signal orange, sage); knob in natural aluminium.
- **Printability:** re-split the top as its own part, about 180 × 40 mm, printed on end or flat. It is the easiest two-tone (separate parts) and also makes the UI board serviceable.
- **Why it fits a desk/event showpiece:** a colour-blocked control surface photographs well from the user's seat and from above, and allows deck colourways per event.

### C. "HALO": guarded ends and carry yoke *(event / carry)*

Each end cap is wrapped by a **halo ring**, a thick printed TPU or ASA ring that sits ~4 mm proud of the PR. The halo protects the cone, acts as an end bumper and gives the speaker a "drum" read.

- **Carry:** a rope or webbing strap clips between the two halos across the back (quick-release anchors). Set down, the strap falls behind. Picked up, it carries like a bag.
- **Grille:** expanded or coarse perforated aluminium over the front.
- **Display and knob:** set into a short recessed top "cockpit" between the halos.

```
 end view            front view (strap behind)
  ╭─────╮             ╭╮════════════ strap ════════════╭╮
 ╭│ ( ) │╮ ◄ halo     ││▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒││
 ╰│     │╯   ring     ││▒▒ expanded / open perf Al ▒▒▒▒▒▒││
  ╰─────╯             ╰╯▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔╰╯
                      halos double as feet → no extra foot needed
```

- **CMF:** body in mid-grey ASA (UV) or PETG; halos in a saturated TPU accent; strap in a contrasting rope or webbing; raw aluminium grille.
- **Printability:** halos print flat in TPU 95A (0.6 mm nozzle [F16b]). A halo adds ~8 mm length, so check the 220 mm envelope only if it is printed integral with the shell. As separate parts it is fine. A halo must stay out of the PR's near-field opening, so the constraints agent should give the minimum ring ID and standoff.
- **Why it fits a desk/event showpiece:** it can be thrown in a bag and set on a booth table, and the bright halos are the brand cue from across a room.

### D. "FACET": eight-sided prism *(engineering-honest; needs constraints check)*

The round tube becomes a rounded **octagonal prism** (R ≈ 6 mm on the corners), and every facet has a job:

- **Front facet (φ = 0°):** woofers.
- **Upper-front facets (φ = 45°):** tweeters. The facet normal at 45° is close to the decided 40° tweeter axis (verify).
- **Top facet:** UI, with no flat pads stuck on a curve.
- **Bottom facet:** foot.

Flat facets let the grille be a **press-brake-bent flat sheet**, not a rolled one, which is easier to get crisp at home with a bending brake or clamp-and-block. The end caps are octagonal "frames" around a round PR bezel.

```
 end view              front view
   ┌───┐  top: UI       ┌───────[ ● ○ ○   (◉)   ⊚ ]───────┐
  ╱  ◆  ╲ 45°: tweeters ├╱◯╲▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒╱◯╲┤ ← tweeter facets
 │ (◎)   │ front: woof  │▒▒▒▒▒▒( )▒▒▒▒▒▒▒▒▒▒( )▒▒▒▒▒▒▒▒▒▒▒│
  ╲     ╱                └────────────────────────────────┘
   └───┘  bottom: foot
```

- **CMF:** satin dark-green or slate matte PETG; bent perforated aluminium in natural or black; ASA end frames printed face-down on textured PEI in a lighter tone; a white-on-dark laser-etched or printed index line on the knob.
- **Printability:** prints on end as now, so facets are vertical walls. Facet edges hide the Z-seam (seams hide best at sharp edges [F9][F10]).
- **Geometry check:** an octagon with the same 47.5 mm inradius is ~5.5 % larger in area than the circle and 103 mm across the corners. Keep the inradius, or shrink it to hold ~0.82 L net, and check woofer flange depth (≥ 30 mm off axis) and the PR annulus.
- **Why it fits a desk/event showpiece:** a distinctive, non-derivative silhouette that sits stably, explains its own engineering at a glance, and makes the top a proper control desk.

### E. "KNIT": soft textile wrap *(home/desk)*

The softest, most furniture-like direction. A single grille-cloth sleeve wraps the full 360°, except a **pebble-shaped UI island** on top (a printed inset carrying display, buttons and knob) and the end caps. The cloth terminates in grooves under contrasting end caps that carry a turned-wood-look or solid-colour bezel around each PR.

```
 end view            front view
   _◜‾◝_ ◄ pebble    ┌──────────────(  ○ ○ ◉ ⊚  )────────────┐
  /░░░░░\  UI island ◎░░░░░░░░░░░░░ knit / cloth ░░░░░░░░░░░░◎
 |░░░░░░░|           │░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
  \░░░░░/            └──────────────────────────────────────┘
```

- **CMF:** heather-grey or oatmeal cloth (PE 260-337 grey [H4b]); end caps in warm sand or terracotta matte PETG; brass-coloured or natural aluminium knob; a printed or fabric pull tab as the carry loop.
- **Printability:** the shells stay as they are, and their outside finish no longer matters (cloth hides layer lines, seams and the split). Only the end caps and the UI island are show parts.
  - The cloth needs a printed under-frame with 2–3 mm stand-off over the woofer openings.
  - The standard cloth is not flame-retardant [H4b]; Mellotone is [H4c].
- **Why it fits a desk/event showpiece:** it looks like a design-store object, not a gadget. Cloth plus solid caps is the fastest route to "finished" with an FDM printer.

---

## 6. Top CMF / finishing recommendations

1. **Two colours plus one metal, nothing else.** Retire the orange plungers and blue lens. The display lens is dark/smoked, and the plungers match the body.
2. **The knob is the jewel.** Use a knurled aluminium knob around Ø25 mm (SAK-006 [H6], or Adafruit 5527 at 20 mm [H5]), sunk into a recess, ≤ 8 mm proud.
3. **Use matte PETG in a mid or light neutral** for shells [F11][F10b]. Avoid glossy black on show faces. Move to ASA for a show unit that will see sun [F15].
4. **Get textures for free from the print orientation.**
   - End caps get the textured-PEI finish (they already print face-down) [F8].
   - Shells get fuzzy skin painted onto large non-mating surfaces only [F1][F2], or the intended ring texture (direction A).
5. **Hide the Z-seam** in the rear split or a modelled reveal, and use scarf seams [F4][F5].
6. **Every split is a designed shadow line** (1.6 mm lap, 0.4 mm chamfers) [F9b], and no fastener is visible on the front or top.
7. **Frame each PR** with a bezel or halo ring that turns the squircle frame round and hides the screws.
8. **Grille is one continuous piece with no exposed edges.** Pick fine perforation if the acoustics allow it (23–40 % open [H1]), and put the tweeters under it to kill the "face".
9. **Use a continuous foot rail** (silicone cord in a groove [H9b]) or Bumpons on a flat [H8], never dots on a curve.
10. **Paint only the hero unit.** PETG needs an adhesion primer, then filler primer and P400 [F13][F13b]. Vapour smoothing is for ASA only and costs detail [F14b].

---

## 7. Sources

**Products**
- [1] JBL Flip 7, global: https://global.jbl.com/FLIP-7.html; spec sheet: https://resources.sevenoakssoundandvision.co.uk/images/manuals/JBL_FLIP_7_Specsheet_EN%20-EMEA.pdf
- [2] SoundGuys Flip 7 (four rubber bumpers): https://www.soundguys.com/jbl-flip-7-99963/
- [3] Target Flip 7 listing (recycled plastic + fabric): https://www.target.com/p/-/A-95032702
- [4] JBL Charge 6: https://global.jbl.com/CHARGE-6.html; [4b] What Hi-Fi: https://www.whathifi.com/speakers/wireless-speakers/jbl-charge-6; Tom's Guide (embossed logo, top buttons): https://www.tomsguide.com/audio/speakers/jbl-charge-6; [4c] Digital Trends (woven fabric wrap): https://qa2.www.digitaltrends.com/home-theater/jbl-charge-6-review
- [5] SoundGuys Charge 6 (detachable handle): https://soundguys.com/jbl-charge-6-review-132332
- [6] SoundGuys Charge 5 (bumpers protect PRs): https://soundguys.com/jbl-charge-5-review-53379; [6b] Pocket-lint Charge 5: https://www.pocket-lint.com/speakers/reviews/jbl/157610-jbl-charge-5-review-waterproof-portable-bluetooth
- [7] UE Boom 4: https://ultimateears.com/en-in/shop/p/boom-4; [7b] RTINGS: https://rtings.com/speaker/reviews/ultimate-ears/boom-4
- [8] Bose SoundLink Flex 2nd Gen specs: https://support.bose.com/s/article/product-specifications-bose-soundlink-flex-portable-speaker-2nd-gen; [8b] B&H: https://www.bhphotovideo.com/c/product/1847844-REG/bose_887612_0200_soundlink_flex_portable_bluetooth.html; [8c] Expert Reviews: https://www.expertreviews.co.uk/?p=1442428
- [9] What Hi-Fi SL Max: https://www.whathifi.com/us/reviews/bose-soundlink-max; [9b] SoundGuys: https://soundguys.com/bose-soundlink-max-review-129228; [9c] B&H: https://www.bhphotovideo.com/c/product/1825201-REG/bose_883848_0100_soundlink_max_portable_speaker.html; [9d] Bose rope handle: https://bose.com/p/accessories/bose-soundlink-max-rope-carrying-strap/CMSP-SLMAX-HNDLPLSC.html
- [10] What Hi-Fi A1 2nd Gen: https://www.whathifi.com/reviews/bang-and-olufsen-beosound-a1-2nd-gen; [10b] Trusted Reviews: https://www.trustedreviews.com/reviews/bang-olufsen-beosound-a1-2nd-gen; [10c] B&O catalogue (ArchiExpo): https://pdf.archiexpo.com/pdf/bang-olufsen/beosound-a1-2-n-d-gen/5258-403421.html
- [11] Beosound Explore product sheet: https://cdn.shopify.com/s/files/1/0290/7566/9076/files/Beosound_Explore_Product_Sheet_English_0001_Feb2021.pdf; [11b] TechRadar: https://www.techradar.com/reviews/bang-and-olufsen-beosound-explore; [11c] B&O catalogue: https://pdf.archiexpo.com/pdf/bang-olufsen/beosound-explore/5258-403513.html
- [12] Marshall Emberton III: https://www.marshall.com/bs/en/product/emberton-iii; [12b] B&H: https://www.bhphotovideo.com/c/product/1840903-REG/marshall_1006884_emberton_iii_black_brass.html
- [13] Marshall Middleton: https://www.marshall.com/eu/en/product/middleton; [13b] Trusted Reviews: https://www.trustedreviews.com/reviews/marshall-middleton; [13c] Expert Reviews: https://www.expertreviews.co.uk/technology/headphones-audio/marshall-middleton-review; [13d] Pocket-lint: https://www.pocket-lint.com/marshall-middleton-review/
- [14] Sonos Roam 2 fact sheet: https://assets.sonos.com/media-kits/hardware/roam2/roam2factsheet.pdf; [14b] What Hi-Fi: https://www.whathifi.com/reviews/sonos-roam-2
- [15] SoundGuys Motion 300: https://soundguys.com/anker-soundcore-motion-300-review-103438; [15b] Cult of Mac: https://www.cultofmac.com/?p=833366
- [16] B&H OB-4: https://www.bhphotovideo.com/c/product/1620727-REG/teenage_engineering_te011as002_us_the_magic_radio_black.html; [16b] Engadget: https://www.engadget.com/teenage-engineering-ob-4-review-150009876.html; [16c] Stuff: https://www.stuff.tv/review/teenage-engineering-ob-4-review
- [17] T3 Mania: https://t3.com/reviews/devialet-mania-review; [17b] Crutchfield: https://www.crutchfield.com/learn/devialet-mania-review.html; [17c] Best Buy owner reviews: https://www.bestbuy.com/product/devialet-mania-portable-bluetooth-and-wi-fi-capability-speaker-deep-black/JV73YQSVVQ/sku/6527343/reviews; [17d] Devialet: https://devialet.com/portable-speakers; [17e] Stuff: https://www.stuff.tv/review/devialet-mania-review
- [18] BGR Beats Pill: https://www.bgr.com/reviews/beats-pill-review; [18b] T3: https://t3.com/reviews/beats-pill-2024-review; [18c] TechRadar: https://www.techradar.com/audio/wireless-bluetooth-speakers/beats-pill-review
- [19] JBL Flip 6 support: https://support.jbl.com/ca/en/speakers/speakers-portable/FLIP-6-.html; [19b] Input: https://www.inverse.com/input/reviews/jbl-flip-6-review-loud-bluetooth-speaker-feels-phone-in; [19c] TechRadar: https://www.techradar.com/reviews/jbl-flip-6

**Finishing / FDM**
- [F1] Prusa, fuzzy skin: https://help.prusa3d.com/article/fuzzy-skin_246186; All3DP defaults: https://all3dp.com/2/prusaslicer-fuzzy-skin-how-to-use-it/
- [F2] OrcaSlicer wiki, fuzzy skin: https://www.orcaslicer.com/wiki/print_settings/others/others_settings_fuzzy_skin
- [F3] Snapmaker, fuzzy skin settings: https://www.snapmaker.com/blog/fuzzy-skin-3d-print/
- [F4] Prusa, seam position: https://help.prusa3d.com/en/article/seam-position_151069; seam painting: https://help.prusa3d.com/en/article/seam-painting_168620
- [F5] OrcaSlicer wiki, seam / scarf joint: https://www.orcaslicer.com/wiki/print_settings/quality/quality_settings_seam
- [F6] Prusa, ironing: https://help.prusa3d.com/en/article/ironing_177488; [F6b] Prusa (CZ) PETG note: https://help.prusa3d.com/cs/article/ironing-zehleni_177488
- [F7] Prusa, variable layer height: https://help.prusa3d.com/en/article/variable-layer-height-function_1750; [F7b] Prusa blog: https://blog.prusa3d.com/smooth-variable-layer-height-awesome-supports-slic3r-prusa-edition_5452/
- [F8] Flashforge, build plate: https://wiki.flashforge.com/en/creator-series/creator-5-series/manual/printing-on-the-build-plate; [F8b] Prusa textured sheet: https://help.prusa3d.com/en/article/textured-steel-sheet_196534; [F8c] All3DP PEI sheets: https://all3dp.com/2/prusa-pei-sheet-textured-powder-coated-steel/
- [F9] Hackaday, shadow line: https://hackaday.com/2023/08/07/enhance-your-enclosures-with-a-shadow-line; [F9b] OpenAT design guide, shadow lines: https://makersmakingchange.github.io/OpenAT_Design_Guide/Design_Elements_For_3D_Printed_Parts/Shadow-Lines.html
- [F10] Hackaday, hiding layer lines: https://hackaday.com/2024/03/04/design-tips-to-hide-layer-lines-in-3d-printed-parts; [F10b] Sovol: https://www.sovol3d.com/blogs/news/simple-ways-to-hide-layer-texture-on-3d-prints
- [F11] All3DP, Bambu PETG Matte: https://all3dp.com/4/bambu-lab-launches-petg-matte-promising-pla-like-printing-with-petg-durability/; Fiberlogy Matte PET-G: https://fiberlogy.com/en/product/matte-petg-filament/; Spectrum PET-G Matt: https://ca.spectrumfilaments.com/collections/pet-g-matt
- [F12] Printago, Orca pause/filament change: https://printago.io/guides/orca-slicer-pause-at-layer; [F12b] Bambu forum, colour-change zit: https://forum.bambulab.com/t/resuming-print-after-switching-filament-colors-leaves-zit/203092; [F12c] Prusa, insert pause at layer: https://help.prusa3d.com/en/article/insert-pause-or-custom-g-code-at-layer_120490
- [F13] All3DP, painting PETG: https://all3dp.com/2/best-paint-for-plastic-pla-abs-petg-nylon/; [F13b] MatterHackers, PETG post-processing: https://www.matterhackers.com/articles/how-to-post-processing-petg-3d-filament; [F13c] Prusa blog, post-processing: https://blog.prusa3d.com/postprocessing-of-3d-prints-step-by-step_29270/; [F13d] Just Paint adhesion test: https://justpaint.org/?p=15484; [F13e] Formlabs, prime and paint: https://formlabs.com/blog/how-to-prime-and-paint-3d-prints/
- [F14] Polymaker wiki, smoothing: https://wiki.polymaker.com/printing-tips/post-processing/smoothing; [F14b] All3DP, vapour smoothing: https://all3dp.com/2/abs-smoothing-a-beginners-guide-to-abs-vapor-smoothing/; [F14c] Xometry: https://www.xometry.com/resources/3d-printing/acetone-vapor-smoothing
- [F15] MatterHackers, outdoor filaments: https://matterhackers.com/articles/the-best-3d-printing-filament-for-outdoor-use
- [F16] Flashforge AD5M Pro: https://flashforge.com/products/adventurer-5m-pro; [F16b] Flashforge TPU guide: https://wiki.flashforge.com/resource/pictures/filament/print_defect_and_solution/tpu_usage_guide.pdf; filament matrix: https://wiki.flashforge.com/en/filaments_and_accessories/filaments_selection_and_applicability/p_m_f; [F16c] Orca/Orca-Flashforge guide: https://eu.flashforge.com/blogs/news/orca-and-orca-flashforge-a-comprehensive-guide
- [F17] McMaster heat-set inserts: https://www.mcmaster.com/heat-set-inserts; [F17b] Prusa / CNC Kitchen inserts: https://www.prusa3d.com/en/product/threaded-inserts-m4-standard-50-pcs
- [F18] Vitsœ, Rams' good design principles (background): https://www.vitsoe.com/us/about/good-design

**Hardware**
- [H1] McMaster perforated aluminium sheets: https://www.mcmaster.com/products/perforated-aluminum-sheets/
- [H2] Zoro 0.032" 3003, Ø0.188" on 0.25", 51 %: https://www.zoro.com/zoro-select-sheet-perf-al-40x36-20ga-0188in-dia-rnd-03032188r250s-36x40/i/G0653834/; [H2b] Zoro Ø0.062": https://www.zoro.com/zoro-select-sheet-perf-al-40x36-20ga-0062in-dia-rnd-03032063r125s-36x40/i/G1396692
- [H3] McMaster expanded aluminium: https://www.mcmaster.com/products/aluminum-expanded-metal
- [H4] Parts Express 260-335 black: https://www.parts-express.com/Speaker-Grill-Cloth-Black-Yard-70-Wide-260-335; [H4b] 260-337 grey: https://www.parts-express.com/Speaker-Grill-Cloth-Gray-Yard-70-Wide-260-337; [H4c] Mellotone 260-332: https://www.parts-express.com/Mellotone-Premium-Black-Speaker-Grill-Cloth-Yard-64-Wide-260-332
- [H5] Adafruit 5527 aluminium knob: https://adafruit.com/product/5527
- [H6] Same Sky aluminium knobs (Mouser): https://www.mouser.com/new/same-sky/same-sky-aluminum-knobs/
- [H7] McMaster set-screw knobs: https://www.mcmaster.com/products/set-screw-knobs/
- [H8] 3M Bumpon SJ5302 (Digi-Key): https://www.digikey.com/en/products/detail/3m/SJ5302-R25/7402682; [H8b] 3M Bumpon datasheet: https://multimedia.3m.com/mws/media/175691O/3mtm-bumpontm-protective-products.pdf
- [H9] McMaster adhesive-back bumpers: https://www.mcmaster.com/products/adhesive-back-bumpers/; [H9b] McMaster silicone cord stock: https://www.mcmaster.com/products/silicone-o-ring-cord-stock/
- [H10] Peak Design Anchor Links (REI): https://www.rei.com/product/128656/peak-design-anchor-links-camera-strap-connectors; [H10b] Adorama: https://www.adorama.com/peak-design-anchor-links-v4-quick-connector-camera-strap/p/pdal4
- [H11] McMaster webbing mounting plates: https://www.mcmaster.com/products/webbing-mounting-plates/; [H11b] webbing: https://mcmaster.com/products/webbing
- [H12] McMaster 5862K116 magnet: https://www.mcmaster.com/product/5862K116/; [H12b] N52 magnets: https://www.mcmaster.com/products/magnets/magnet-grade~n52/
- [H13] Flashforge TPU 95A: https://eu.flashforge.com/products/tpu-95a

*Research note: WebFetch was unavailable in this session. Facts come from search-result extracts of the linked pages. McMaster tables were fragmentary, so re-check part numbers live before ordering.*
