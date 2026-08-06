---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

This skill also applies when the requested artifact is an HTML-based presentation, training deck, course page set, one-page-at-a-time walkthrough, or any "PPT-like" experience implemented in HTML. In those cases, treat the work as frontend information design, not as a PowerPoint clone. The goal is to create a sequence of polished web pages that happen to be viewed one page at a time.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: Claude is capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box and committing fully to a distinctive vision.

## HTML Page-Based Experiences

Use this section when the user asks for HTML pages that behave like slides, courseware, internal training material, product walkthroughs, visual explainers, report pages, or a sequence of 16:9 screens.

### Core framing

Do not treat "PPT" language literally when the user is asking for HTML. Users often say PPT to mean "one idea per screen" or "a page-by-page presentation effect." The implementation should use web-native layout, component thinking, responsive constraints, and frontend visual systems. It should not mechanically copy office-slide templates.

A good HTML page-based artifact feels like:
- A set of designed web scenes
- A product interface or information dashboard where appropriate
- An editorial explainer with strong hierarchy
- A training manual made of visual components

It should not feel like:
- A Markdown document printed into rectangles
- A repeated title-plus-card template
- A screenshot of a generic slide deck
- A decorative landing page with content pasted into it

### Design workflow

Before writing the HTML/CSS, decide the page taxonomy. Different kinds of pages need different compositions:

- Cover: brand or course name, short subtitle, one strong visual system
- Agenda/map: timeline, module path, journey diagram
- Tension/problem: one dominant claim, comparison bars, evidence blocks
- Concept: layered diagram, matrix, capability boundary, "is / is not" structure
- Process: 3-5 step flow, input/output cards, checkpoints
- Case study: scenario -> input -> AI/tool action -> human review -> output
- Prompt/code: large readable code block, variable tags, copy-oriented structure
- Data/table: restrained table with clear emphasis, not spreadsheet dumping
- Summary: action cards, key takeaways, next steps

Pick components based on the content. Do not default to cards. Cards are appropriate for repeated peer items, but hierarchy often needs asymmetry, scale shifts, diagrams, bars, tables, or workflows.

### Information architecture

Extract UI-ready content from source material:

- Use page titles as headings, not file/parser labels
- Convert paragraphs into labels, steps, short claims, tags, and conclusions
- Keep generator notes, design reminders, and internal planning text out of the visible page
- Give each page one primary visual job
- Keep each screen readable from a presentation distance
- Preserve long prompts/code exactly when they are the artifact users need to copy

If a page has too much content, redesign the representation before shrinking text. Use grouping, progressive emphasis, compact tables, or visual hierarchy. Tiny text is a failure of structure, not a solution.

### Visual system

Define CSS variables for color, type scale, spacing, borders, shadows, and page dimensions. Maintain a coherent system across pages while varying composition by page type.

For professional training and operational artifacts:
- Prefer quiet, precise palettes with one strong accent
- Use typography to create confidence and hierarchy
- Use restrained borders and shadows, not decorative excess
- Keep border radius modest, generally 8px or less unless the product language calls for more
- Use diagrams, lines, labels, chips, code panels, tables, and status markers as real interface components
- Avoid purple-blue gradient defaults, vague tech glow, decorative blobs, unrelated stock imagery, and one-note color themes

### Layout constraints

For fixed-format pages such as 16:9 course screens:
- Use `aspect-ratio` and stable page dimensions
- Use grid or flex layouts with explicit tracks
- Prevent dynamic content from resizing the page unexpectedly
- Verify that the longest labels fit inside their containers
- Keep text from overlapping, clipping, or being pushed outside the page
- Design mobile behavior intentionally: scale the page, stack content, or provide a scrollable page frame depending on the user's need

### Motion and interaction

Default to a strong static design. Add motion only when it improves comprehension:
- Subtle page reveal or section emphasis is fine
- Current-page navigation, keyboard movement, print styles, or copy buttons can be useful
- Avoid complex animations that distract from reading or presenting

### Verification

Before calling the work complete, inspect representative page types, not just the first screen:
- Cover
- A dense concept page
- A process page
- A prompt/code page
- A table/data page if present
- A final summary page

Check for count consistency, 16:9 framing, readable text, non-overlap, uncut code/prompts, and coherent visual rhythm across the sequence.
