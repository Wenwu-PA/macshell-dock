-- Host-rendered glyph, tooltip and hover; no polling or custom surface.
function update()
    barWidget.setGlyph("layout-bottombar")
    barWidget.setText("")
    barWidget.setTooltip("MacDock Control")
end
function onClick()
    noctalia.togglePanel("wenwu/macdock:control")
end
update()
