"""MacroWide - 주식 분석 및 경제 지표 시각화 대시보드"""

import reflex as rx


class State(rx.State):
    """앱 상태 관리"""
    pass


def navbar() -> rx.Component:
    """네비게이션 바"""
    return rx.box(
        rx.hstack(
            # 로고
            rx.hstack(
                rx.icon("trending-up", size=28, color="#10b981"),
                rx.text(
                    "MacroWide",
                    class_name="text-xl font-bold text-emerald-400",
                ),
                align="center",
                spacing="2",
            ),
            # 네비게이션 메뉴
            rx.hstack(
                rx.link("대시보드", href="/", class_name="text-gray-300 hover:text-emerald-400"),
                rx.link("주식분석", href="/stocks", class_name="text-gray-300 hover:text-emerald-400"),
                rx.link("경제지표", href="/indicators", class_name="text-gray-300 hover:text-emerald-400"),
                spacing="6",
            ),
            # 우측 버튼
            rx.color_mode.button(size="2", variant="ghost"),
            justify="between",
            align="center",
            width="100%",
        ),
        class_name="fixed top-0 left-0 right-0 z-50 px-6 py-4 bg-slate-900/90 backdrop-blur border-b border-slate-700/50",
    )


def hero_section() -> rx.Component:
    """히어로 섹션"""
    return rx.box(
        rx.vstack(
            rx.text(
                "MACRO WIDE",
                class_name="text-sm font-semibold tracking-widest text-emerald-400 mb-4",
            ),
            rx.heading(
                "글로벌 경제를 한눈에 파악하세요",
                class_name="text-4xl md:text-5xl font-bold text-white leading-tight mb-6",
            ),
            rx.text(
                "실시간 주식 데이터, 경제 지표, 시장 분석을 통해 더 나은 투자 결정을 내리세요.",
                class_name="text-lg text-gray-400 max-w-xl mb-8",
            ),
            rx.hstack(
                rx.button(
                    "대시보드 시작하기",
                    rx.icon("arrow-right", size=18),
                    class_name="bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-3 rounded-lg font-semibold",
                ),
                rx.button(
                    "더 알아보기",
                    variant="outline",
                    class_name="border-slate-600 text-gray-300 hover:bg-slate-800 px-6 py-3 rounded-lg",
                ),
                spacing="4",
            ),
            align="start",
            class_name="max-w-2xl",
        ),
        class_name="min-h-[70vh] flex items-center pt-24 pb-12",
    )


def indicator_card(name: str, value: str, change: str, is_positive: bool) -> rx.Component:
    """경제 지표 카드"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(name, class_name="text-gray-400 text-sm font-medium"),
                rx.icon(
                    "trending-up" if is_positive else "trending-down",
                    size=16,
                    color="#10b981" if is_positive else "#ef4444",
                ),
                justify="between",
                width="100%",
            ),
            rx.text(value, class_name="text-2xl font-bold text-white"),
            rx.text(
                change,
                class_name=f"text-sm font-semibold {'text-emerald-400' if is_positive else 'text-red-400'}",
            ),
            align="start",
            spacing="2",
            width="100%",
        ),
        class_name="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 hover:border-emerald-500/50 transition-all cursor-pointer",
    )


def indicators_section() -> rx.Component:
    """경제 지표 섹션"""
    return rx.box(
        rx.vstack(
            rx.heading("실시간 시장 지표", class_name="text-2xl font-bold text-white mb-6"),
            rx.box(
                indicator_card("KOSPI", "2,687.42", "+1.24%", True),
                indicator_card("KOSDAQ", "872.15", "-0.32%", False),
                indicator_card("S&P 500", "6,032.38", "+0.89%", True),
                indicator_card("NASDAQ", "19,478.91", "+1.15%", True),
                indicator_card("USD/KRW", "1,428.50", "-0.15%", False),
                indicator_card("기준금리", "3.00%", "0.00%", True),
                class_name="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 w-full",
            ),
            width="100%",
        ),
        class_name="py-12",
    )


def features_section() -> rx.Component:
    """기능 소개 섹션"""
    return rx.box(
        rx.vstack(
            rx.heading(
                "왜 MacroWide인가요?",
                class_name="text-3xl font-bold text-white text-center mb-12",
            ),
            rx.hstack(
                # 기능 1
                rx.box(
                    rx.vstack(
                        rx.box(
                            rx.icon("line-chart", size=28, color="#34d399"),
                            class_name="w-14 h-14 bg-emerald-500/10 rounded-xl flex items-center justify-center mb-4",
                        ),
                        rx.heading("실시간 시장 데이터", class_name="text-xl font-bold text-white mb-2"),
                        rx.text("주요 지수, 환율, 원자재 가격을 실시간으로 모니터링하세요.", class_name="text-gray-400 text-center"),
                        align="center",
                    ),
                    class_name="flex-1 p-6",
                ),
                # 기능 2
                rx.box(
                    rx.vstack(
                        rx.box(
                            rx.icon("brain", size=28, color="#34d399"),
                            class_name="w-14 h-14 bg-emerald-500/10 rounded-xl flex items-center justify-center mb-4",
                        ),
                        rx.heading("AI 기반 분석", class_name="text-xl font-bold text-white mb-2"),
                        rx.text("인공지능이 분석한 시장 트렌드와 투자 인사이트를 제공합니다.", class_name="text-gray-400 text-center"),
                        align="center",
                    ),
                    class_name="flex-1 p-6",
                ),
                # 기능 3
                rx.box(
                    rx.vstack(
                        rx.box(
                            rx.icon("bell", size=28, color="#34d399"),
                            class_name="w-14 h-14 bg-emerald-500/10 rounded-xl flex items-center justify-center mb-4",
                        ),
                        rx.heading("맞춤 알림", class_name="text-xl font-bold text-white mb-2"),
                        rx.text("관심 종목과 지표에 대한 실시간 알림을 받아보세요.", class_name="text-gray-400 text-center"),
                        align="center",
                    ),
                    class_name="flex-1 p-6",
                ),
                spacing="6",
                width="100%",
                class_name="flex-col md:flex-row",
            ),
            width="100%",
        ),
        class_name="py-16 border-t border-slate-800",
    )


def footer() -> rx.Component:
    """푸터"""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("trending-up", size=20, color="#10b981"),
                rx.text("MacroWide", class_name="font-semibold text-gray-400"),
                spacing="2",
            ),
            rx.text(
                "© 2026 MacroWide. All rights reserved.",
                class_name="text-gray-500 text-sm",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        class_name="py-8 border-t border-slate-800",
    )


def index() -> rx.Component:
    """메인 페이지"""
    return rx.box(
        navbar(),
        rx.box(
            hero_section(),
            indicators_section(),
            features_section(),
            footer(),
            class_name="max-w-7xl mx-auto px-6",
        ),
        class_name="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950",
    )


app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="teal",
    ),
)
app.add_page(index, title="MacroWide - 글로벌 경제 대시보드")
