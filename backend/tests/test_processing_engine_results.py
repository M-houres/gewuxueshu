from pathlib import Path

from docx import Document
from sqlalchemy.orm import Session

from app.models import TaskType
from app.services.processing_engine import ProcessingEngine


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    doc = Document()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    doc.save(path)


def test_rewrite_process_uses_report_summary(tmp_path: Path, db_session: Session, monkeypatch) -> None:
    source_path = tmp_path / "paper.docx"
    report_path = tmp_path / "report.docx"
    output_path = tmp_path / "result.docx"

    _write_docx(
        source_path,
        [
            "研究表明，这一方法非常重要，而且很多场景都可以看出类似趋势。",
            "这个结论在教学和管理实践中具有较强参考价值。",
        ],
    )
    _write_docx(
        report_path,
        [
            "全文AIGC检测报告",
            "总体风险 52%",
            "高风险段落占比 24%",
        ],
    )

    monkeypatch.setattr(ProcessingEngine, "_run_llm", lambda self, *_args, **_kwargs: None)
    monkeypatch.setattr(ProcessingEngine, "_run_algo_package", lambda self, *_args, **_kwargs: None)

    engine = ProcessingEngine(db_session)
    result = engine.process(
        TaskType.REWRITE,
        "cnki",
        source_path,
        output_path,
        task_id=1,
        report_path=report_path,
    )

    assert output_path.exists()
    assert result.result_json["type"] == "rewrite"
    assert result.result_json["report_summary"]["available"] is True
    assert result.result_json["report_summary"]["pressure"] == "high"
    assert len(result.result_json["report_summary"]["metrics"]) >= 1
    assert len(result.result_json["review_points"]) >= 1
    assert isinstance(result.result_json["output_preview"], str)
    assert result.result_json["source_stats"]["char_count"] > 0
    assert result.result_json["output_stats"]["char_count"] > 0


def test_aigc_detect_returns_structured_result(tmp_path: Path, db_session: Session, monkeypatch) -> None:
    source_path = tmp_path / "paper.txt"
    output_path = tmp_path / "result.pdf"
    source_path.write_text(
        "本研究围绕教学改革展开讨论。"
        "研究表明该方案在多个学院中具有稳定的执行路径，因此能够快速复制。"
        "\n"
        "此外，文章采用一致的段落结构和重复性的总结语句，这会提高自动化写作特征。",
        encoding="utf-8",
    )

    monkeypatch.setattr(ProcessingEngine, "_run_algo_package", lambda self, *_args, **_kwargs: None)

    engine = ProcessingEngine(db_session)
    result = engine.process(TaskType.AIGC_DETECT, "cnki", source_path, output_path, task_id=2)

    assert output_path.exists()
    assert result.result_json["type"] == "aigc_detect"
    assert "summary" in result.result_json
    assert "risk_band" in result.result_json
    assert result.result_json["simulation_profile"] == "cnki_like"
    assert result.result_json["source_stats"]["char_count"] > 0
    assert len(result.result_json["risk_paragraphs"]) >= 1
    content = output_path.read_bytes()
    assert content.startswith(b"%PDF-")
    assert b"Detection Summary" in content
    assert b"GEWU Academic" not in content


def test_aigc_detect_platform_profiles_are_close_but_not_identical(
    tmp_path: Path, db_session: Session, monkeypatch
) -> None:
    source_path = tmp_path / "paper_platform.txt"
    source_path.write_text(
        "本研究基于教学管理数据，围绕课程评价机制展开分析。\n"
        "文章包含连续论证句、固定连接词和重复总结表达，用于模拟AIGC风险检测场景。\n"
        "在不同平台规则下，分值应保持相近，但因评分偏好不同会存在轻微差异。",
        encoding="utf-8",
    )
    monkeypatch.setattr(ProcessingEngine, "_run_algo_package", lambda self, *_args, **_kwargs: None)

    engine = ProcessingEngine(db_session)
    results = {}
    for platform in ("cnki", "vip", "paperpass"):
        output_path = tmp_path / f"{platform}.pdf"
        result = engine.process(TaskType.AIGC_DETECT, platform, source_path, output_path, task_id=100)
        results[platform] = float(result.result_json["score_pct"])
        assert output_path.exists()

    assert len(set(round(value, 2) for value in results.values())) >= 2
    assert max(results.values()) - min(results.values()) <= 15
