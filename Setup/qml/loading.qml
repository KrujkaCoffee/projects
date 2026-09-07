import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    anchors.fill: parent
    color: bgColor

    BusyIndicator {
        anchors.centerIn: parent
        running: true
        width: 64
        height: 64
    }

    Text {
        anchors.top: parent.verticalCenter
        anchors.topMargin: 50
        anchors.horizontalCenter: parent.horizontalCenter
        text: "Загрузка..."
        font.pointSize: 12
    }
}