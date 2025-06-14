# -*- coding: utf-8 -*-
"""
Sistema de Comunidade
Implementa funcionalidades de comunidade, fóruns, compartilhamento e networking
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
from pathlib import Path
import hashlib

class PostType(Enum):
    """Tipos de post"""
    QUESTION = "question"
    SHOWCASE = "showcase"
    TUTORIAL = "tutorial"
    DISCUSSION = "discussion"
    ANNOUNCEMENT = "announcement"
    TIP = "tip"

class PostStatus(Enum):
    """Status do post"""
    ACTIVE = "active"
    CLOSED = "closed"
    PINNED = "pinned"
    ARCHIVED = "archived"
    DELETED = "deleted"

class UserRole(Enum):
    """Papéis do usuário na comunidade"""
    MEMBER = "member"
    CONTRIBUTOR = "contributor"
    MODERATOR = "moderator"
    EXPERT = "expert"
    ADMIN = "admin"

class VoteType(Enum):
    """Tipos de voto"""
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"

@dataclass
class User:
    """Usuário da comunidade"""
    id: str
    username: str
    email: str
    display_name: str
    bio: str
    avatar_url: str
    role: UserRole
    reputation: int
    badges: List[str]
    skills: List[str]
    location: str
    website: str
    joined_at: datetime
    last_active: datetime
    is_active: bool

@dataclass
class Post:
    """Post da comunidade"""
    id: str
    author_id: str
    title: str
    content: str
    post_type: PostType
    status: PostStatus
    category: str
    tags: List[str]
    attachments: List[Dict[str, str]]
    votes_up: int
    votes_down: int
    views: int
    replies_count: int
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    is_solved: bool
    accepted_answer_id: Optional[str]

@dataclass
class Reply:
    """Resposta a um post"""
    id: str
    post_id: str
    author_id: str
    content: str
    parent_reply_id: Optional[str]  # Para respostas aninhadas
    votes_up: int
    votes_down: int
    is_accepted: bool
    created_at: datetime
    updated_at: datetime

@dataclass
class Badge:
    """Badge/conquista do usuário"""
    id: str
    name: str
    description: str
    icon: str
    category: str
    requirements: Dict[str, Any]
    points: int
    rarity: str  # common, rare, epic, legendary

class CommunitySystem:
    """Sistema principal da comunidade"""
    
    def __init__(self, db_path: str = "community.sqlite"):
        self.db_path = db_path
        self._init_database()
        self._init_badges()
        
    def _init_database(self):
        """Inicializa o banco de dados"""
        with sqlite3.connect(self.db_path) as conn:
            # Tabela de usuários
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    bio TEXT DEFAULT '',
                    avatar_url TEXT DEFAULT '',
                    role TEXT NOT NULL DEFAULT 'member',
                    reputation INTEGER DEFAULT 0,
                    badges TEXT NOT NULL DEFAULT '[]',
                    skills TEXT NOT NULL DEFAULT '[]',
                    location TEXT DEFAULT '',
                    website TEXT DEFAULT '',
                    joined_at TEXT NOT NULL,
                    last_active TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Tabela de posts
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    author_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    post_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    category TEXT NOT NULL,
                    tags TEXT NOT NULL DEFAULT '[]',
                    attachments TEXT NOT NULL DEFAULT '[]',
                    votes_up INTEGER DEFAULT 0,
                    votes_down INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    replies_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    is_solved BOOLEAN DEFAULT FALSE,
                    accepted_answer_id TEXT,
                    FOREIGN KEY (author_id) REFERENCES users (id)
                )
            """)
            
            # Tabela de respostas
            conn.execute("""
                CREATE TABLE IF NOT EXISTS replies (
                    id TEXT PRIMARY KEY,
                    post_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    parent_reply_id TEXT,
                    votes_up INTEGER DEFAULT 0,
                    votes_down INTEGER DEFAULT 0,
                    is_accepted BOOLEAN DEFAULT FALSE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (post_id) REFERENCES posts (id),
                    FOREIGN KEY (author_id) REFERENCES users (id),
                    FOREIGN KEY (parent_reply_id) REFERENCES replies (id)
                )
            """)
            
            # Tabela de votos
            conn.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    vote_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, target_id, target_type)
                )
            """)
            
            # Tabela de badges
            conn.execute("""
                CREATE TABLE IF NOT EXISTS badges (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT NOT NULL,
                    icon TEXT NOT NULL,
                    category TEXT NOT NULL,
                    requirements TEXT NOT NULL,
                    points INTEGER NOT NULL,
                    rarity TEXT NOT NULL
                )
            """)
            
            # Tabela de badges dos usuários
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_badges (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    badge_id TEXT NOT NULL,
                    earned_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (badge_id) REFERENCES badges (id),
                    UNIQUE(user_id, badge_id)
                )
            """)
            
            # Tabela de seguindo/seguidores
            conn.execute("""
                CREATE TABLE IF NOT EXISTS follows (
                    id TEXT PRIMARY KEY,
                    follower_id TEXT NOT NULL,
                    following_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (follower_id) REFERENCES users (id),
                    FOREIGN KEY (following_id) REFERENCES users (id),
                    UNIQUE(follower_id, following_id)
                )
            """)
            
            # Tabela de projetos compartilhados
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_projects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    project_data TEXT NOT NULL,
                    preview_image TEXT,
                    tags TEXT NOT NULL DEFAULT '[]',
                    is_public BOOLEAN DEFAULT TRUE,
                    likes INTEGER DEFAULT 0,
                    downloads INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.commit()
    
    def _init_badges(self):
        """Inicializa badges padrão"""
        default_badges = [
            {
                'id': 'first-post',
                'name': 'Primeiro Post',
                'description': 'Criou seu primeiro post na comunidade',
                'icon': '🎉',
                'category': 'Participação',
                'requirements': {'posts_created': 1},
                'points': 10,
                'rarity': 'common'
            },
            {
                'id': 'helpful',
                'name': 'Prestativo',
                'description': 'Recebeu 10 votos positivos em respostas',
                'icon': '🤝',
                'category': 'Contribuição',
                'requirements': {'reply_upvotes': 10},
                'points': 50,
                'rarity': 'rare'
            },
            {
                'id': 'expert',
                'name': 'Especialista',
                'description': 'Teve 5 respostas aceitas',
                'icon': '🎓',
                'category': 'Conhecimento',
                'requirements': {'accepted_answers': 5},
                'points': 100,
                'rarity': 'epic'
            },
            {
                'id': 'community-leader',
                'name': 'Líder da Comunidade',
                'description': 'Alcançou 1000 pontos de reputação',
                'icon': '👑',
                'category': 'Liderança',
                'requirements': {'reputation': 1000},
                'points': 200,
                'rarity': 'legendary'
            },
            {
                'id': 'showcase-master',
                'name': 'Mestre do Showcase',
                'description': 'Compartilhou 10 projetos',
                'icon': '🎨',
                'category': 'Criatividade',
                'requirements': {'projects_shared': 10},
                'points': 75,
                'rarity': 'rare'
            }
        ]
        
        with sqlite3.connect(self.db_path) as conn:
            for badge in default_badges:
                conn.execute("""
                    INSERT OR IGNORE INTO badges 
                    (id, name, description, icon, category, requirements, points, rarity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    badge['id'], badge['name'], badge['description'],
                    badge['icon'], badge['category'], json.dumps(badge['requirements']),
                    badge['points'], badge['rarity']
                ))
            conn.commit()
    
    def create_user(self, 
                   username: str,
                   email: str,
                   display_name: str,
                   bio: str = "",
                   avatar_url: str = "") -> str:
        """Cria um novo usuário"""
        user_id = str(uuid.uuid4())
        now = datetime.now()
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            display_name=display_name,
            bio=bio,
            avatar_url=avatar_url,
            role=UserRole.MEMBER,
            reputation=0,
            badges=[],
            skills=[],
            location="",
            website="",
            joined_at=now,
            last_active=now,
            is_active=True
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO users (
                    id, username, email, display_name, bio, avatar_url,
                    role, reputation, badges, skills, location, website,
                    joined_at, last_active, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user.id, user.username, user.email, user.display_name,
                user.bio, user.avatar_url, user.role.value, user.reputation,
                json.dumps(user.badges), json.dumps(user.skills),
                user.location, user.website, user.joined_at.isoformat(),
                user.last_active.isoformat(), user.is_active
            ))
            conn.commit()
        
        return user_id
    
    def create_post(self, 
                   author_id: str,
                   title: str,
                   content: str,
                   post_type: PostType,
                   category: str,
                   tags: List[str] = None,
                   attachments: List[Dict[str, str]] = None) -> str:
        """Cria um novo post"""
        post_id = str(uuid.uuid4())
        now = datetime.now()
        
        post = Post(
            id=post_id,
            author_id=author_id,
            title=title,
            content=content,
            post_type=post_type,
            status=PostStatus.ACTIVE,
            category=category,
            tags=tags or [],
            attachments=attachments or [],
            votes_up=0,
            votes_down=0,
            views=0,
            replies_count=0,
            created_at=now,
            updated_at=now,
            last_activity=now,
            is_solved=False,
            accepted_answer_id=None
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO posts (
                    id, author_id, title, content, post_type, status, category,
                    tags, attachments, votes_up, votes_down, views, replies_count,
                    created_at, updated_at, last_activity, is_solved, accepted_answer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post.id, post.author_id, post.title, post.content,
                post.post_type.value, post.status.value, post.category,
                json.dumps(post.tags), json.dumps(post.attachments),
                post.votes_up, post.votes_down, post.views, post.replies_count,
                post.created_at.isoformat(), post.updated_at.isoformat(),
                post.last_activity.isoformat(), post.is_solved, post.accepted_answer_id
            ))
            conn.commit()
        
        # Verifica badges
        self._check_user_badges(author_id)
        
        return post_id
    
    def create_reply(self, 
                    post_id: str,
                    author_id: str,
                    content: str,
                    parent_reply_id: Optional[str] = None) -> str:
        """Cria uma resposta"""
        reply_id = str(uuid.uuid4())
        now = datetime.now()
        
        reply = Reply(
            id=reply_id,
            post_id=post_id,
            author_id=author_id,
            content=content,
            parent_reply_id=parent_reply_id,
            votes_up=0,
            votes_down=0,
            is_accepted=False,
            created_at=now,
            updated_at=now
        )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO replies (
                    id, post_id, author_id, content, parent_reply_id,
                    votes_up, votes_down, is_accepted, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                reply.id, reply.post_id, reply.author_id, reply.content,
                reply.parent_reply_id, reply.votes_up, reply.votes_down,
                reply.is_accepted, reply.created_at.isoformat(),
                reply.updated_at.isoformat()
            ))
            
            # Atualiza contador de respostas do post
            conn.execute(
                "UPDATE posts SET replies_count = replies_count + 1, last_activity = ? WHERE id = ?",
                (now.isoformat(), post_id)
            )
            
            conn.commit()
        
        # Verifica badges
        self._check_user_badges(author_id)
        
        return reply_id
    
    def vote(self, user_id: str, target_id: str, target_type: str, vote_type: VoteType) -> bool:
        """Adiciona ou atualiza voto"""
        vote_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            try:
                # Remove voto anterior se existir
                old_vote = conn.execute(
                    "SELECT vote_type FROM votes WHERE user_id = ? AND target_id = ? AND target_type = ?",
                    (user_id, target_id, target_type)
                ).fetchone()
                
                if old_vote:
                    # Remove voto anterior das contagens
                    if target_type == "post":
                        if old_vote[0] == "upvote":
                            conn.execute("UPDATE posts SET votes_up = votes_up - 1 WHERE id = ?", (target_id,))
                        else:
                            conn.execute("UPDATE posts SET votes_down = votes_down - 1 WHERE id = ?", (target_id,))
                    elif target_type == "reply":
                        if old_vote[0] == "upvote":
                            conn.execute("UPDATE replies SET votes_up = votes_up - 1 WHERE id = ?", (target_id,))
                        else:
                            conn.execute("UPDATE replies SET votes_down = votes_down - 1 WHERE id = ?", (target_id,))
                    
                    # Remove voto
                    conn.execute(
                        "DELETE FROM votes WHERE user_id = ? AND target_id = ? AND target_type = ?",
                        (user_id, target_id, target_type)
                    )
                
                # Adiciona novo voto
                conn.execute("""
                    INSERT INTO votes (id, user_id, target_id, target_type, vote_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (vote_id, user_id, target_id, target_type, vote_type.value, now.isoformat()))
                
                # Atualiza contagens
                if target_type == "post":
                    if vote_type == VoteType.UPVOTE:
                        conn.execute("UPDATE posts SET votes_up = votes_up + 1 WHERE id = ?", (target_id,))
                    else:
                        conn.execute("UPDATE posts SET votes_down = votes_down + 1 WHERE id = ?", (target_id,))
                elif target_type == "reply":
                    if vote_type == VoteType.UPVOTE:
                        conn.execute("UPDATE replies SET votes_up = votes_up + 1 WHERE id = ?", (target_id,))
                    else:
                        conn.execute("UPDATE replies SET votes_down = votes_down + 1 WHERE id = ?", (target_id,))
                
                conn.commit()
                
                # Atualiza reputação do autor
                self._update_reputation(target_id, target_type, vote_type)
                
                return True
                
            except sqlite3.IntegrityError:
                return False
    
    def accept_answer(self, post_id: str, reply_id: str, author_id: str) -> bool:
        """Marca resposta como aceita"""
        with sqlite3.connect(self.db_path) as conn:
            # Verifica se o usuário é o autor do post
            cursor = conn.execute(
                "SELECT author_id FROM posts WHERE id = ?", (post_id,)
            )
            post_author = cursor.fetchone()
            
            if not post_author or post_author[0] != author_id:
                return False
            
            # Remove aceitação anterior
            conn.execute(
                "UPDATE replies SET is_accepted = FALSE WHERE post_id = ?",
                (post_id,)
            )
            
            # Marca nova resposta como aceita
            conn.execute(
                "UPDATE replies SET is_accepted = TRUE WHERE id = ?",
                (reply_id,)
            )
            
            # Atualiza post
            conn.execute(
                "UPDATE posts SET is_solved = TRUE, accepted_answer_id = ? WHERE id = ?",
                (reply_id, post_id)
            )
            
            conn.commit()
            
            # Atualiza reputação do autor da resposta
            cursor = conn.execute(
                "SELECT author_id FROM replies WHERE id = ?", (reply_id,)
            )
            reply_author = cursor.fetchone()
            if reply_author:
                self._add_reputation(reply_author[0], 15)  # Bonus por resposta aceita
                self._check_user_badges(reply_author[0])
            
            return True
    
    def share_project(self, 
                     user_id: str,
                     title: str,
                     description: str,
                     project_data: Dict[str, Any],
                     tags: List[str] = None,
                     preview_image: str = "") -> str:
        """Compartilha um projeto"""
        project_id = str(uuid.uuid4())
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO shared_projects (
                    id, user_id, title, description, project_data,
                    preview_image, tags, is_public, likes, downloads,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id, user_id, title, description,
                json.dumps(project_data), preview_image,
                json.dumps(tags or []), True, 0, 0,
                now.isoformat(), now.isoformat()
            ))
            conn.commit()
        
        # Verifica badges
        self._check_user_badges(user_id)
        
        return project_id
    
    def get_posts(self, 
                 category: Optional[str] = None,
                 post_type: Optional[PostType] = None,
                 sort_by: str = "recent",
                 limit: int = 20,
                 offset: int = 0) -> List[Dict[str, Any]]:
        """Obtém posts com filtros"""
        query = """
            SELECT p.*, u.username, u.display_name, u.avatar_url, u.reputation
            FROM posts p
            JOIN users u ON p.author_id = u.id
            WHERE p.status = 'active'
        """
        params = []
        
        if category:
            query += " AND p.category = ?"
            params.append(category)
        
        if post_type:
            query += " AND p.post_type = ?"
            params.append(post_type.value)
        
        # Ordenação
        if sort_by == "recent":
            query += " ORDER BY p.last_activity DESC"
        elif sort_by == "popular":
            query += " ORDER BY (p.votes_up - p.votes_down) DESC, p.views DESC"
        elif sort_by == "unanswered":
            query += " AND p.replies_count = 0 ORDER BY p.created_at DESC"
        
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Obtém estatísticas do usuário"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Estatísticas básicas
            cursor = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM posts WHERE author_id = ?) as posts_count,
                    (SELECT COUNT(*) FROM replies WHERE author_id = ?) as replies_count,
                    (SELECT COUNT(*) FROM replies WHERE author_id = ? AND is_accepted = TRUE) as accepted_answers,
                    (SELECT SUM(votes_up) FROM posts WHERE author_id = ?) as post_upvotes,
                    (SELECT SUM(votes_up) FROM replies WHERE author_id = ?) as reply_upvotes,
                    (SELECT COUNT(*) FROM shared_projects WHERE user_id = ?) as projects_shared
            """, (user_id, user_id, user_id, user_id, user_id, user_id))
            
            stats = dict(cursor.fetchone())
            
            # Badges do usuário
            cursor = conn.execute("""
                SELECT b.* FROM badges b
                JOIN user_badges ub ON b.id = ub.badge_id
                WHERE ub.user_id = ?
                ORDER BY ub.earned_at DESC
            """, (user_id,))
            
            badges = [dict(row) for row in cursor.fetchall()]
            stats['badges'] = badges
            
            return stats
    
    def _update_reputation(self, target_id: str, target_type: str, vote_type: VoteType):
        """Atualiza reputação do autor"""
        points = 2 if vote_type == VoteType.UPVOTE else -1
        
        with sqlite3.connect(self.db_path) as conn:
            if target_type == "post":
                cursor = conn.execute(
                    "SELECT author_id FROM posts WHERE id = ?", (target_id,)
                )
            elif target_type == "reply":
                cursor = conn.execute(
                    "SELECT author_id FROM replies WHERE id = ?", (target_id,)
                )
            else:
                return
            
            author = cursor.fetchone()
            if author:
                self._add_reputation(author[0], points)
    
    def _add_reputation(self, user_id: str, points: int):
        """Adiciona pontos de reputação"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET reputation = reputation + ? WHERE id = ?",
                (points, user_id)
            )
            conn.commit()
    
    def _check_user_badges(self, user_id: str):
        """Verifica e concede badges ao usuário"""
        stats = self.get_user_stats(user_id)
        
        with sqlite3.connect(self.db_path) as conn:
            # Obtém badges disponíveis
            cursor = conn.execute("SELECT * FROM badges")
            badges = cursor.fetchall()
            
            for badge in badges:
                badge_id = badge[0]
                requirements = json.loads(badge[5])
                
                # Verifica se já tem o badge
                existing = conn.execute(
                    "SELECT id FROM user_badges WHERE user_id = ? AND badge_id = ?",
                    (user_id, badge_id)
                ).fetchone()
                
                if existing:
                    continue
                
                # Verifica requisitos
                earned = True
                for req_key, req_value in requirements.items():
                    if req_key == 'reputation':
                        cursor = conn.execute(
                            "SELECT reputation FROM users WHERE id = ?", (user_id,)
                        )
                        user_rep = cursor.fetchone()[0]
                        if user_rep < req_value:
                            earned = False
                            break
                    elif req_key in stats:
                        if stats[req_key] < req_value:
                            earned = False
                            break
                
                # Concede badge
                if earned:
                    badge_user_id = str(uuid.uuid4())
                    now = datetime.now()
                    
                    conn.execute("""
                        INSERT INTO user_badges (id, user_id, badge_id, earned_at)
                        VALUES (?, ?, ?, ?)
                    """, (badge_user_id, user_id, badge_id, now.isoformat()))
                    
                    # Adiciona pontos de reputação
                    self._add_reputation(user_id, badge[6])  # badge points
            
            conn.commit()

# Instância global
community_system = CommunitySystem()