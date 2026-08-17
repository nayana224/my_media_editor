APP_STYLE = """
QWidget#root,
QDialog {
    background: #111318;
    color: #e7eaf0;
}

QLabel {
    color: #e7eaf0;
}

QLabel#appTitle {
    font-size: 26px;
    font-weight: 700;
}

QLabel#appSubtitle,
QLabel#dialogDescription {
    color: #8f96a3;
    font-size: 13px;
}

QLabel#sectionTitle {
    color: #8f96a3;
    font-size: 11px;
    font-weight: 700;
    padding-bottom: 4px;
}

QLabel#fileInfo {
    color: #a9b0bd;
    font-size: 12px;
    padding-left: 2px;
}

QFrame#libraryCard,
QFrame#previewCard,
QFrame#controlCard {
    background: #171a20;
    border: 1px solid #2a2f39;
    border-radius: 12px;
}

QListWidget#mediaList {
    background: #12151a;
    color: #dce1e9;
    border: 0;
    border-radius: 8px;
    padding: 4px;
}

QListWidget#mediaList::item {
    min-height: 34px;
    padding: 0 8px;
    border-radius: 6px;
}

QListWidget#mediaList::item:hover {
    background: #20242c;
}

QListWidget#mediaList::item:selected {
    background: #2b355d;
    color: #ffffff;
}

QLabel#imagePreview {
    background: #0c0e12;
    border-radius: 12px;
}

QLabel#dropIcon {
    color: #8ba4ff;
    font-size: 42px;
    font-weight: 300;
}

QLabel#dropTitle {
    font-size: 17px;
    font-weight: 600;
}

QLabel#dropDescription {
    color: #808895;
    font-size: 12px;
}

QPushButton {
    min-height: 36px;
    padding: 0 16px;
    border-radius: 8px;
    font-weight: 600;
}

QPushButton#primaryButton {
    background: #6f88ff;
    color: #ffffff;
    border: 1px solid #7f96ff;
}

QPushButton#primaryButton:hover {
    background: #7b93ff;
}

QPushButton#primaryButton:pressed {
    background: #6079ec;
}

QPushButton#secondaryButton {
    background: #20242c;
    color: #dfe3eb;
    border: 1px solid #343a46;
}

QPushButton#secondaryButton:hover {
    background: #282d37;
}

QPushButton#toolButton {
    background: transparent;
    color: #c3c9d3;
    border: 1px solid #343a46;
}

QPushButton#toolButton:hover {
    background: #20242c;
}

QPushButton:disabled {
    color: #5e6570;
    background: #171a20;
    border-color: #292e37;
}

QDoubleSpinBox {
    min-height: 34px;
    padding: 0 8px;
    color: #e7eaf0;
    background: #171a20;
    border: 1px solid #343a46;
    border-radius: 7px;
}

QSlider::groove:horizontal {
    height: 5px;
    background: #323844;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #6f88ff;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    width: 14px;
    margin: -5px 0;
    background: #dce3ff;
    border: 2px solid #6f88ff;
    border-radius: 7px;
}

QLabel#timeLabel {
    color: #929aa7;
    font-family: monospace;
    font-size: 12px;
}

QToolTip {
    color: #e7eaf0;
    background: #20242c;
    border: 1px solid #343a46;
    padding: 5px;
}
"""
