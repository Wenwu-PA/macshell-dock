import QtQuick
Item {
    id: panel
    property var backdrop: null
    property bool live: false
    property bool frozen: false
    property bool dark: false
    property real k: 1
    property real radius: 16
    property real bodyH: 28
    property real tailW: 0
    property real tailH: 0
    property real tailTipR: 3
    property real tailX: width / 2
    property real blurAmount: 0
    default property alias content: body.data
    height: bodyH + tailH
    Rectangle {
        width: parent.width; height: panel.bodyH
        radius: panel.radius
        color: panel.dark ? "#ef262629" : "#f5f5f5f7"
        border.width: 1
        border.color: panel.dark ? "#30ffffff" : "#18000000"
    }
    Item { id: body; width: parent.width; height: panel.bodyH }
}
