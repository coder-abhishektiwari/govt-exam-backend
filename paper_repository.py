import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import INDEX_FILE, PAPERS_DIR


class PaperRepository:
    def __init__(self, papers_dir: Path = PAPERS_DIR, index_file: Path = INDEX_FILE):
        self.papers_dir = papers_dir.resolve()
        self.index_file = index_file

    def load_index(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self.index_file.exists():
            return {"upcoming_exams": []}

        with self.index_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

        # Support both old "papers" and new "upcoming_exams" format
        exams = data.get("upcoming_exams") or data.get("papers", [])
        if not isinstance(exams, list):
            raise ValueError("question_papers/index.json must contain a 'upcoming_exams' or 'papers' list")
        return {"upcoming_exams": exams}

    def save_index(self, index_data: Dict[str, Any]) -> None:
        self._write_json(self.index_file, index_data)

    def list_metadata(self) -> List[Dict[str, Any]]:
        return self.load_index()["upcoming_exams"]

    def load(self, paper_id: str) -> Optional[Dict[str, Any]]:
        metadata = self._find_metadata(paper_id)
        if metadata is None:
            return None

        paper_path = self._paper_path(metadata)
        if not paper_path.is_file():
            return None

        with paper_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save(self, paper_id: str, paper_data: Dict[str, Any]) -> None:
        index = self.load_index()
        papers = index["papers"]
        existing = next((paper for paper in papers if paper.get("id") == paper_id), None)
        file_name = (existing or {}).get("file", f"{paper_id}.json")
        paper_path = self._resolve_file(file_name)

        self._write_json(paper_path, paper_data)

        metadata = self._metadata_from_paper(paper_data, file_name)
        if existing is None:
            papers.append(metadata)
        else:
            existing.update(metadata)
        self.save_index(index)

    def delete(self, paper_id: str) -> bool:
        index = self.load_index()
        papers = index["papers"]
        metadata = next((paper for paper in papers if paper.get("id") == paper_id), None)
        if metadata is None:
            return False

        paper_path = self._paper_path(metadata)
        if paper_path.exists():
            paper_path.unlink()

        index["papers"] = [paper for paper in papers if paper.get("id") != paper_id]
        self.save_index(index)
        return True

    def _find_metadata(self, paper_id: str) -> Optional[Dict[str, Any]]:
        return next(
            (paper for paper in self.list_metadata() if paper.get("id") == paper_id),
            None,
        )

    def _paper_path(self, metadata: Dict[str, Any]) -> Path:
        # Try to get file name from metadata, otherwise generate from ID
        file_name = metadata.get("file") or f"{metadata.get('id', '')}.json"
        if not file_name or file_name == ".json":
            raise ValueError(f"Paper '{metadata.get('id', 'unknown')}' has no valid file mapping")
        return self._resolve_file(file_name)

    def _resolve_file(self, file_name: str) -> Path:
        path = (self.papers_dir / file_name).resolve()
        if path.parent != self.papers_dir or path.suffix.lower() != ".json":
            raise ValueError(f"Invalid paper file mapping: {file_name}")
        return path

    @staticmethod
    def _metadata_from_paper(
        paper_data: Dict[str, Any], file_name: str
    ) -> Dict[str, Any]:
        metadata = paper_data.get("metadata", {})
        return {
            "id": paper_data.get("id"),
            "title": paper_data.get("title"),
            "display_name": paper_data.get("display_name"),
            "subject": paper_data.get("subject"),
            "exam_board": paper_data.get("exam_board"),
            "total_questions": paper_data.get("total_questions"),
            "filename": paper_data.get("filename"),
            "file": file_name,
            "version": paper_data.get("version", "1.0"),
            "description": metadata.get("description", ""),
        }

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temp_path.replace(path)


paper_repository = PaperRepository()
