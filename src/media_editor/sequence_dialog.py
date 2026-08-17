from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from media_editor.media import MediaKind
from media_editor.project import MediaAsset


PATH_ROLE = Qt.ItemDataRole.UserRole


class SequenceDialog(QDialog):
    """여러 video를 한 줄 sequence로 배치하고 순서를 정한다."""

    def __init__(
        self,
        assets: list[MediaAsset],
        current_asset: MediaAsset | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sequence / Concat")
        self.setModal(True)
        self.resize(860, 560)
        self.setMinimumSize(720, 480)

        self.available_list = QListWidget()
        self.available_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.sequence_list = QListWidget()
        self.sequence_list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.sequence_list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
        )
        self.sequence_list.setDefaultDropAction(Qt.DropAction.MoveAction)

        for asset in assets:
            if asset.kind is not MediaKind.VIDEO:
                continue
            self._add_path_item(self.available_list, asset.path)

        append_button = QPushButton("Append →")
        append_button.setObjectName("primaryButton")
        append_button.clicked.connect(self._append_selected)

        remove_button = QPushButton("Remove")
        remove_button.setObjectName("secondaryButton")
        remove_button.clicked.connect(self._remove_selected)

        clear_button = QPushButton("Clear")
        clear_button.setObjectName("secondaryButton")
        clear_button.clicked.connect(self.sequence_list.clear)

        self.available_list.itemDoubleClicked.connect(
            lambda _item: self._append_selected()
        )

        if current_asset is not None and current_asset.kind is MediaKind.VIDEO:
            self._add_path_item(self.sequence_list, current_asset.path)

        left = QVBoxLayout()
        left.addWidget(QLabel("MEDIA VIDEOS"))
        left.addWidget(self.available_list)

        center = QVBoxLayout()
        center.addStretch()
        center.addWidget(append_button)
        center.addWidget(remove_button)
        center.addWidget(clear_button)
        center.addStretch()

        right = QVBoxLayout()
        right.addWidget(QLabel("SEQUENCE · 위에서 아래 순서로 재생"))
        right.addWidget(self.sequence_list)
        hint = QLabel(
            "Sequence 항목을 마우스로 드래그해 순서를 바꿀 수 있습니다."
        )
        hint.setObjectName("dialogDescription")
        right.addWidget(hint)

        content = QHBoxLayout()
        content.addLayout(left, stretch=1)
        content.addLayout(center)
        content.addLayout(right, stretch=1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            "Export Sequence"
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        title = QLabel("영상들을 순서대로 이어 붙입니다.")
        title.setObjectName("dialogDescription")
        layout.addWidget(title)
        layout.addLayout(content, stretch=1)
        layout.addWidget(buttons)

    @property
    def sequence_paths(self) -> list[Path]:
        return [
            Path(self.sequence_list.item(index).data(PATH_ROLE))
            for index in range(self.sequence_list.count())
        ]

    def _append_selected(self) -> None:
        for item in self.available_list.selectedItems():
            path = Path(item.data(PATH_ROLE))
            self._add_path_item(self.sequence_list, path)

    def _remove_selected(self) -> None:
        rows = sorted(
            {self.sequence_list.row(item) for item in self.sequence_list.selectedItems()},
            reverse=True,
        )
        for row in rows:
            self.sequence_list.takeItem(row)

    def _accept_if_valid(self) -> None:
        if self.sequence_list.count() < 2:
            return
        self.accept()

    @staticmethod
    def _add_path_item(widget: QListWidget, path: Path) -> None:
        item = QListWidgetItem(path.name)
        item.setToolTip(str(path))
        item.setData(PATH_ROLE, str(path))
        widget.addItem(item)
