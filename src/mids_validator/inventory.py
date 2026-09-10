"""Discover and describe the contents of a MIDS dataset."""

from dataclasses import dataclass
from pathlib import Path

from mids_validator.file_types import is_nifti_file


VALID_DATATYPE_DIRECTORIES = frozenset({"mr-anat", "mr-quant", "ct", "rx"})


@dataclass(frozen=True)
class DatasetInventory:
    """A read-only list of paths found below one dataset root."""

    root: Path
    root_items: tuple[Path, ...]
    all_items: tuple[Path, ...]

    def children(self, directory: Path) -> tuple[Path, ...]:
        """Return already-discovered direct children of ``directory``."""

        return tuple(
            item for item in self.all_items if item.parent == directory
        )

    def subject_directories(self) -> tuple[Path, ...]:
        """Return root directories that declare themselves as subjects."""

        return tuple(
            item
            for item in self.root_items
            if item.is_dir() and item.name.startswith("sub-")
        )

    def session_directories(
        self,
        subject_directory: Path,
    ) -> tuple[Path, ...]:
        """Return session directories immediately below one subject."""

        return tuple(
            item
            for item in self.children(subject_directory)
            if item.is_dir() and item.name.startswith("ses-")
        )

    def datatype_directories(
        self,
        subject_directory: Path,
    ) -> tuple[Path, ...]:
        """Return recognized datatype directories for one subject."""

        datatype_directories = [
            item
            for item in self.children(subject_directory)
            if item.is_dir() and item.name in VALID_DATATYPE_DIRECTORIES
        ]

        for session_directory in self.session_directories(subject_directory):
            datatype_directories.extend(
                item
                for item in self.children(session_directory)
                if item.is_dir() and item.name in VALID_DATATYPE_DIRECTORIES
            )

        return tuple(datatype_directories)

    def relative_path(self, path: Path) -> str:
        """Return a path relative to the dataset root."""

        return str(path.relative_to(self.root))

    def nifti_image_paths(self) -> tuple[Path, ...]:
        """Return discovered NIfTI images in recognized datatype folders."""

        image_paths: list[Path] = []

        for subject_directory in self.subject_directories():
            for datatype_directory in self.datatype_directories(
                subject_directory
            ):
                image_paths.extend(
                    path
                    for path in self.children(datatype_directory)
                    if is_nifti_file(path)
                )

        return tuple(image_paths)


def build_inventory(dataset_root: Path) -> DatasetInventory:
    """Scan a valid dataset directory once and return its inventory."""

    root = dataset_root.resolve()
    all_items = tuple(sorted(root.rglob("*"), key=lambda path: str(path)))
    root_items = tuple(item for item in all_items if item.parent == root)

    return DatasetInventory(
        root=root,
        root_items=root_items,
        all_items=all_items,
    )
