# -*- coding: utf-8 -*-
"""
Callbacks para os Novos Sistemas
Implementa toda a funcionalidade backend para os sistemas de:
- Feedback
- Comunidade
- Tutoriais
- Notificações
- Gamificação
- Personalização
- Colaboração
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL, MATCH
import dash_bootstrap_components as dbc
import pandas as pd
import json
import uuid
from datetime import datetime, timedelta
from dash.exceptions import PreventUpdate

from utils.logger import log_info, log_error, log_warning, log_debug
from utils.feedback_system import feedback_system
from utils.community_system import community_system
from utils.tutorial_system import tutorial_system
from utils.notification_system import notification_system
from utils.gamification_system import gamification_system
from utils.personalization_system import personalization_system
from utils.collaboration_system import collaboration_system

# Variável global para a instância do cache
cache = None

def register_callbacks(app, cache_instance):
    """Registra todos os callbacks dos novos sistemas"""
    global cache
    cache = cache_instance
    
    # ===== CALLBACKS DO SISTEMA DE FEEDBACK =====
    
    @app.callback(
        [Output('feedback-toast', 'is_open', allow_duplicate=True),
         Output('feedback-toast', 'children', allow_duplicate=True),
         Output('feedback-title', 'value'),
         Output('feedback-description', 'value')],
        [Input('submit-feedback', 'n_clicks')],
        [State('feedback-type', 'value'),
         State('feedback-priority', 'value'),
         State('feedback-title', 'value'),
         State('feedback-description', 'value')],
        prevent_initial_call=True
    )
    def submit_feedback(n_clicks, feedback_type, priority, title, description):
        """Processa envio de feedback"""
        if not n_clicks:
            raise PreventUpdate
            
        try:
            if not title or not description:
                return True, dbc.Alert("Por favor, preencha todos os campos obrigatórios.", color="warning"), title, description
            
            # Criar feedback
            feedback_id = feedback_system.create_feedback(
                user_id="user_001",  # Em produção, pegar do sistema de autenticação
                title=title,
                description=description,
                feedback_type=feedback_type,
                priority=priority
            )
            
            if feedback_id:
                log_info(f"Feedback criado com sucesso: {feedback_id}")
                return True, dbc.Alert("Feedback enviado com sucesso! Obrigado pela sua contribuição.", color="success"), "", ""
            else:
                return True, dbc.Alert("Erro ao enviar feedback. Tente novamente.", color="danger"), title, description
                
        except Exception as e:
            log_error(f"Erro ao processar feedback: {e}")
            return True, dbc.Alert("Erro interno. Tente novamente mais tarde.", color="danger"), title, description
    
    # ===== CALLBACKS DO SISTEMA DE GAMIFICAÇÃO =====
    
    @app.callback(
        [Output('user-level', 'children'),
         Output('user-xp', 'children'),
         Output('user-progress', 'value'),
         Output('user-progress', 'label'),
         Output('badges-grid', 'children')],
        [Input('gamification-refresh', 'n_clicks'),
         Input('url', 'pathname')],
        prevent_initial_call=False
    )
    def update_gamification_data(n_clicks, pathname):
        """Atualiza dados de gamificação do usuário"""
        try:
            user_id = "user_001"  # Em produção, pegar do sistema de autenticação
            
            # Obter dados do usuário
            user_data = gamification_system.get_user_stats(user_id)
            
            if not user_data:
                # Criar usuário se não existir
                gamification_system.create_user(user_id, "Usuário Teste")
                user_data = gamification_system.get_user_stats(user_id)
            
            level = user_data.get('level', 1)
            xp = user_data.get('experience_points', 0)
            next_level_xp = level * 100  # XP necessário para próximo nível
            progress = (xp % 100)  # Progresso no nível atual
            
            # Obter badges do usuário
            user_badges = gamification_system.get_user_badges(user_id)
            available_badges = gamification_system.get_available_badges()
            
            # Criar grid de badges
            badges_grid = []
            for badge in available_badges:
                is_earned = any(ub['badge_id'] == badge['id'] for ub in user_badges)
                badge_color = "success" if is_earned else "light"
                icon_color = "text-success" if is_earned else "text-muted"
                
                badge_card = dbc.Col([
                    html.Div([
                        html.I(className=f"fas fa-trophy fa-2x {icon_color} mb-2"),
                        html.H6(badge['name'], className="mb-1"),
                        html.P(badge['description'], className="small text-muted")
                    ], className=f"text-center p-3 border rounded bg-{badge_color}")
                ], md=4, className="mb-3")
                
                badges_grid.append(badge_card)
            
            return (
                f"Nível {level}",
                f"Pontos: {xp}",
                progress,
                f"{progress}/100 XP",
                dbc.Row(badges_grid)
            )
            
        except Exception as e:
            log_error(f"Erro ao atualizar gamificação: {e}")
            return "Nível 1", "Pontos: 0", 0, "0/100 XP", html.Div()
    
    # ===== CALLBACKS DO SISTEMA DE PERSONALIZAÇÃO =====
    
    @app.callback(
        Output('personalization-toast', 'is_open', allow_duplicate=True),
        [Input('theme-selector', 'value'),
         Input('layout-selector', 'value')],
        prevent_initial_call=True
    )
    def save_personalization_settings(theme, layout):
        """Salva configurações de personalização"""
        try:
            user_id = "user_001"  # Em produção, pegar do sistema de autenticação
            
            # Salvar preferências de tema
            if theme:
                personalization_system.set_user_preference(
                    user_id, "interface", "theme", theme
                )
            
            # Salvar preferências de layout
            if layout:
                personalization_system.set_user_preference(
                    user_id, "interface", "layout", layout
                )
            
            log_info(f"Configurações de personalização salvas para usuário {user_id}")
            return True
            
        except Exception as e:
            log_error(f"Erro ao salvar personalização: {e}")
            return False
    
    # ===== CALLBACKS DO SISTEMA DE NOTIFICAÇÕES =====
    
    @app.callback(
        [Output('notifications-list', 'children'),
         Output('notifications-count', 'children')],
        [Input('notifications-refresh', 'n_clicks'),
         Input('mark-all-read', 'n_clicks')],
        prevent_initial_call=False
    )
    def update_notifications(refresh_clicks, mark_read_clicks):
        """Atualiza lista de notificações"""
        try:
            user_id = "user_001"  # Em produção, pegar do sistema de autenticação
            
            # Marcar todas como lidas se solicitado
            if mark_read_clicks:
                notification_system.mark_all_as_read(user_id)
            
            # Obter notificações do usuário
            notifications = notification_system.get_user_notifications(user_id)
            unread_count = len([n for n in notifications if not n.get('is_read', False)])
            
            if not notifications:
                notifications_list = html.P(
                    "Nenhuma notificação no momento.", 
                    className="text-muted text-center py-4"
                )
            else:
                notifications_items = []
                for notif in notifications[:10]:  # Mostrar apenas as 10 mais recentes
                    bg_color = "bg-light" if notif.get('is_read', False) else "bg-primary bg-opacity-10"
                    
                    item = dbc.ListGroupItem([
                        html.Div([
                            html.H6(notif.get('title', 'Notificação'), className="mb-1"),
                            html.P(notif.get('message', ''), className="mb-1"),
                            html.Small(
                                notif.get('created_at', datetime.now()).strftime("%d/%m/%Y %H:%M"),
                                className="text-muted"
                            )
                        ])
                    ], className=bg_color)
                    
                    notifications_items.append(item)
                
                notifications_list = dbc.ListGroup(notifications_items)
            
            count_badge = dbc.Badge(
                str(unread_count), 
                color="danger" if unread_count > 0 else "secondary",
                className="ms-2"
            )
            
            return notifications_list, count_badge
            
        except Exception as e:
            log_error(f"Erro ao atualizar notificações: {e}")
            return html.P("Erro ao carregar notificações.", className="text-danger"), dbc.Badge("0", color="secondary")
    
    # ===== CALLBACKS DO SISTEMA DE TUTORIAIS =====
    
    @app.callback(
        [Output('tutorial-progress', 'value'),
         Output('tutorial-progress-text', 'children'),
         Output('tutorials-list', 'children')],
        [Input('tutorial-complete', 'n_clicks'),
         Input('url', 'pathname')],
        [State('tutorial-id', 'data')],
        prevent_initial_call=False
    )
    def update_tutorial_progress(complete_clicks, pathname, tutorial_id):
        """Atualiza progresso dos tutoriais"""
        try:
            user_id = "user_001"  # Em produção, pegar do sistema de autenticação
            
            # Marcar tutorial como completo se solicitado
            if complete_clicks and tutorial_id:
                tutorial_system.complete_tutorial(user_id, tutorial_id)
            
            # Obter progresso do usuário
            progress = tutorial_system.get_user_progress(user_id)
            total_tutorials = 3  # Número total de tutoriais disponíveis
            completed = len(progress.get('completed_tutorials', []))
            progress_percent = (completed / total_tutorials) * 100
            
            # Criar lista de tutoriais
            tutorials = [
                {
                    'id': 'intro',
                    'title': 'Introdução ao DataMindVV',
                    'description': 'Aprenda os conceitos básicos da plataforma',
                    'level': 'Iniciante',
                    'duration': '15 min',
                    'completed': 'intro' in progress.get('completed_tutorials', [])
                },
                {
                    'id': 'database',
                    'title': 'Conectando Bancos de Dados',
                    'description': 'Como conectar diferentes tipos de bancos de dados',
                    'level': 'Intermediário',
                    'duration': '25 min',
                    'completed': 'database' in progress.get('completed_tutorials', [])
                },
                {
                    'id': 'visualizations',
                    'title': 'Criando Visualizações Avançadas',
                    'description': 'Técnicas avançadas de visualização de dados',
                    'level': 'Avançado',
                    'duration': '45 min',
                    'completed': 'visualizations' in progress.get('completed_tutorials', [])
                }
            ]
            
            tutorials_items = []
            for tutorial in tutorials:
                level_color = {
                    'Iniciante': 'success',
                    'Intermediário': 'warning',
                    'Avançado': 'danger'
                }.get(tutorial['level'], 'secondary')
                
                completed_icon = "fas fa-check-circle text-success" if tutorial['completed'] else "far fa-circle text-muted"
                
                item = dbc.ListGroupItem([
                    html.Div([
                        html.Div([
                            html.I(className=f"{completed_icon} me-2"),
                            html.H5(tutorial['title'], className="mb-1 d-inline"),
                        ]),
                        html.P(tutorial['description'], className="mb-1"),
                        html.Div([
                            dbc.Badge(tutorial['level'], color=level_color, className="me-2"),
                            dbc.Badge(tutorial['duration'], color="info")
                        ])
                    ])
                ])
                
                tutorials_items.append(item)
            
            tutorials_list = dbc.ListGroup(tutorials_items)
            
            return (
                progress_percent,
                f"Tutoriais Concluídos: {completed}/{total_tutorials}",
                tutorials_list
            )
            
        except Exception as e:
            log_error(f"Erro ao atualizar tutoriais: {e}")
            return 0, "Tutoriais Concluídos: 0/3", html.Div()
    
    # ===== CALLBACKS DO SISTEMA DE COLABORAÇÃO =====
    
    @app.callback(
        Output('collaboration-toast', 'is_open', allow_duplicate=True),
        [Input('share-dashboard', 'n_clicks'),
         Input('create-session', 'n_clicks'),
         Input('invite-user', 'n_clicks')],
        prevent_initial_call=True
    )
    def handle_collaboration_actions(share_clicks, session_clicks, invite_clicks):
        """Processa ações de colaboração"""
        try:
            ctx = callback_context
            if not ctx.triggered:
                raise PreventUpdate
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            user_id = "user_001"  # Em produção, pegar do sistema de autenticação
            
            if button_id == 'share-dashboard' and share_clicks:
                # Compartilhar dashboard
                share_id = collaboration_system.share_resource(
                    owner_id=user_id,
                    resource_type="dashboard",
                    resource_id="main_dashboard",
                    share_type="view"
                )
                log_info(f"Dashboard compartilhado: {share_id}")
                return True
                
            elif button_id == 'create-session' and session_clicks:
                # Criar sessão colaborativa
                session_id = collaboration_system.create_collaboration_session(
                    creator_id=user_id,
                    resource_type="dashboard",
                    resource_id="main_dashboard"
                )
                log_info(f"Sessão colaborativa criada: {session_id}")
                return True
                
            elif button_id == 'invite-user' and invite_clicks:
                # Convidar usuário (simulado)
                notification_system.create_notification(
                    user_id="user_002",  # Usuário convidado
                    title="Convite para Colaboração",
                    message=f"Você foi convidado por {user_id} para colaborar em um projeto.",
                    notification_type="collaboration_invite"
                )
                log_info(f"Convite enviado para colaboração")
                return True
            
            return False
            
        except Exception as e:
            log_error(f"Erro em ação de colaboração: {e}")
            return False
    
    # ===== CALLBACKS DO SISTEMA DE COMUNIDADE =====
    
    @app.callback(
        [Output('community-stats', 'children'),
         Output('community-posts', 'children')],
        [Input('community-refresh', 'n_clicks'),
         Input('url', 'pathname')],
        prevent_initial_call=False
    )
    def update_community_data(refresh_clicks, pathname):
        """Atualiza dados da comunidade"""
        try:
            # Obter estatísticas da comunidade
            stats = community_system.get_community_stats()
            
            stats_cards = dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(str(stats.get('total_users', 0)), className="text-primary"),
                            html.P("Usuários Ativos", className="mb-0")
                        ])
                    ])
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(str(stats.get('total_posts', 0)), className="text-success"),
                            html.P("Posts Publicados", className="mb-0")
                        ])
                    ])
                ], md=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4(str(stats.get('shared_projects', 0)), className="text-info"),
                            html.P("Projetos Compartilhados", className="mb-0")
                        ])
                    ])
                ], md=4)
            ])
            
            # Posts recentes (simulado)
            posts = html.P("Nenhum post ainda. Seja o primeiro a compartilhar!", className="text-muted text-center py-4")
            
            return stats_cards, posts
            
        except Exception as e:
            log_error(f"Erro ao atualizar comunidade: {e}")
            return html.Div(), html.Div()
    
    log_info("Callbacks dos sistemas registrados com sucesso")