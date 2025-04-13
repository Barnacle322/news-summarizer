from __future__ import annotations

import datetime
from collections.abc import Sequence

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, MappedAsDataclass, mapped_column

from ..extensions import db


class Article(MappedAsDataclass, db.Model, unsafe_hash=True):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, init=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    topic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    published_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), init=False
    )

    @staticmethod
    def get_all() -> Sequence[Article] | None:
        return db.session.scalars(db.select(Article)).all()

    @staticmethod
    def get_by_id(id: int) -> Article | None:
        return db.session.scalar(db.select(Article).where(Article.id == id))

    @staticmethod
    def get_by_url(url: str) -> Article | None:
        return db.session.scalar(db.select(Article).where(Article.url == url))

    @staticmethod
    def get_recent_articles(limit: int = 20) -> Sequence[Article] | None:
        return db.session.scalars(
            db.select(Article).order_by(Article.published_at.desc()).limit(limit)
        ).all()

    @staticmethod
    def search_by_keywords(keywords: str, limit: int = 20) -> Sequence[Article] | None:
        search_terms = [f"%{term.strip()}%" for term in keywords.split()]
        query = db.select(Article)
        for term in search_terms:
            query = query.where(
                (Article.title.ilike(term))
                | (Article.summary.ilike(term))
                | (Article.content.ilike(term))
            )
        return db.session.scalars(
            query.order_by(Article.published_at.desc()).limit(limit)
        ).all()

    @staticmethod
    def get_by_topic(topic: str, limit: int = 20) -> Sequence[Article] | None:
        return db.session.scalars(
            db.select(Article)
            .where(Article.topic.ilike(f"%{topic}%"))
            .order_by(Article.published_at.desc())
            .limit(limit)
        ).all()

    @staticmethod
    def get_by_title(title: str) -> Article | None:
        return db.session.scalar(db.select(Article).where(Article.title == title))
