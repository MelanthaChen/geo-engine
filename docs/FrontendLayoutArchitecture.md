# Frontend Layout Architecture

The application uses one responsive shell for every route. `AppLayout` owns the fixed 256 px sidebar and the remaining viewport width. `ContentContainer` provides consistent page padding and a deliberately generous 1760 px reading boundary, preventing both the former narrow centered column and uncontrolled stretching on very large displays.

## Building blocks

- `Page` provides consistent vertical rhythm and protects grid children with `min-width: 0`.
- `PageHeader` standardizes eyebrow, title, description, context metadata, and page actions.
- `ContentContainer` owns application-wide horizontal padding and maximum width.
- `ResponsiveGrid` uses CSS `auto-fit` and `minmax` so cards wrap according to available space instead of route-specific column counts.
- `Section` is the neutral semantic wrapper for page regions.
- `SplitLayout` and `RightSidebar` keep secondary panels stacked through laptop widths and introduce the optional side column at the 1536 px (`2xl`) breakpoint.
- `StickyToolbar` is the shared shell for pages that need persistent controls.
- The existing UI `Card` remains the canonical visual card primitive.

## Responsive behavior

- Below 1536 px: page content and secondary panels use a single column; card grids wrap automatically.
- From 1536 px: optional side panels become visible as true columns when a page uses `SplitLayout`.
- From 1600 px through large desktop displays: the content area continues expanding until 1760 px.
- The sidebar stays fixed at 256 px and the main region always occupies the rest of the viewport.

Page components should compose these primitives rather than adding `container`, `mx-auto`, `max-w-*`, or fixed page widths locally. Fixed widths remain appropriate only for intentional wide-screen secondary panels inside `SplitLayout`.
