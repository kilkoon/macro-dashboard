"""MacroWide - 주식 분석 및 경제 지표 시각화 대시보드"""

import reflex as rx
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class State(rx.State):
    """앱 상태 관리"""
    indicators: list[dict] = []
    last_updated: str = ""
    is_cached: bool = False
    loading: bool = False
    error: str = ""
    stock_query: str = ""
    selected_symbol: str = "NVDA"
    stock_price: str = "—"
    stock_change: str = "—"
    stock_change_value: str = "—"
    stock_change_pct: str = ""
    stock_change_is_positive: bool = True
    stock_volume: str = "—"
    stock_market_cap: str = "—"
    stock_last_updated: str = ""
    stock_is_cached: bool = False
    stock_loading: bool = False
    stock_error: str = ""
    stock_items: list[dict] = [
        {"symbol": "NVDA", "name": "NVIDIA", "market": "NASDAQ"},
        {"symbol": "IREN", "name": "Iris Energy", "market": "NASDAQ"},
        {"symbol": "RKLB", "name": "Rocket Lab", "market": "NASDAQ"},
    ]

    # 유동성 지표 (경제지표 탭)
    liq_fed_assets: str = "—"
    liq_fed_assets_change: str = "—"
    liq_fed_assets_is_positive: bool = True
    liq_tga_balance: str = "—"
    liq_tga_change: str = "—"
    liq_tga_is_positive: bool = True
    liq_rrp_balance: str = "—"
    liq_rrp_change: str = "—"
    liq_rrp_is_positive: bool = True
    liq_net_liquidity: str = "—"
    liq_net_liquidity_change: str = "—"
    liq_net_is_positive: bool = True
    liq_sp500: str = "—"
    liq_sp500_change: str = "—"
    liq_sp500_is_positive: bool = True
    liq_history: list[dict] = []
    liq_last_updated: str = ""
    liq_is_cached: bool = False
    liq_loading: bool = False
    liq_error: str = ""

    @rx.var
    def liquidity_chart_figure(self) -> go.Figure:
        """Plotly 차트 Figure를 생성합니다."""
        if not self.liq_history:
            # 빈 차트 반환
            fig = go.Figure()
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                annotations=[
                    dict(
                        text="데이터를 불러오는 중...",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(size=16, color="#6b7280"),
                    )
                ],
            )
            return fig

        # 데이터 추출
        dates = [d["date"] for d in self.liq_history]
        net_liq = [d["net_liquidity"] / 1e12 for d in self.liq_history]  # 조 달러
        sp500 = [d["sp500"] for d in self.liq_history]

        # Dual Axis 차트 생성
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # Net Liquidity (왼쪽 Y축)
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=net_liq,
                name="Net Liquidity",
                line=dict(color="#3b82f6", width=2),
                fill="tozeroy",
                fillcolor="rgba(59, 130, 246, 0.1)",
            ),
            secondary_y=False,
        )

        # S&P 500 (오른쪽 Y축)
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=sp500,
                name="S&P 500",
                line=dict(color="#a855f7", width=2),
            ),
            secondary_y=True,
        )

        # 레이아웃 설정
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color="#9ca3af"),
            ),
            hovermode="x unified",
        )

        # Y축 설정
        fig.update_yaxes(
            title_text="Net Liquidity ($T)",
            secondary_y=False,
            gridcolor="rgba(55, 65, 81, 0.5)",
            title_font=dict(color="#3b82f6"),
            tickfont=dict(color="#3b82f6"),
            tickformat=".1f",
            ticksuffix="T",
        )
        fig.update_yaxes(
            title_text="S&P 500",
            secondary_y=True,
            gridcolor="rgba(55, 65, 81, 0.3)",
            title_font=dict(color="#a855f7"),
            tickfont=dict(color="#a855f7"),
            tickformat=",",
        )

        # X축 설정
        fig.update_xaxes(
            gridcolor="rgba(55, 65, 81, 0.3)",
            tickfont=dict(color="#6b7280"),
        )

        return fig

    def set_stock_query(self, value: str):
        self.stock_query = value

    async def set_selected_symbol(self, symbol: str):
        self.selected_symbol = symbol
        await self.load_stock_quote()

    @rx.var
    def filtered_stocks(self) -> list[dict]:
        q = self.stock_query.strip().lower()
        if not q:
            return self.stock_items
        return [
            s
            for s in self.stock_items
            if q in str(s.get("symbol", "")).lower() or q in str(s.get("name", "")).lower()
        ]

    @rx.var
    def selected_stock(self) -> dict:
        for s in self.stock_items:
            if s.get("symbol") == self.selected_symbol:
                return s
        return self.stock_items[0] if self.stock_items else {}

    async def load_indicators(self):
        """무료 데이터 소스에서 시장 지표를 불러옵니다(5분 TTL 캐시)."""
        self.loading = True
        self.error = ""
        try:
            from macro_wide.services.market_data import get_indicators

            indicators, last_updated, is_cached = get_indicators(ttl_seconds=300)
            # Reflex state는 JSON-serializable 타입을 선호하므로 dict로 보관합니다.
            self.indicators = list(indicators)
            self.last_updated = last_updated
            self.is_cached = is_cached
        except Exception:
            # 운영 시에는 로깅을 추가하는 게 좋습니다.
            self.error = "지표 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
            self.is_cached = False
        finally:
            self.loading = False

    async def load_stock_quote(self):
        """선택 종목의 현재가/등락/거래량/시총을 불러옵니다(5분 TTL 캐시)."""
        self.stock_loading = True
        self.stock_error = ""
        try:
            from macro_wide.services.market_data import get_stock_quote

            quote, last_updated, is_cached = get_stock_quote(
                symbol=self.selected_symbol,
                ttl_seconds=300,
            )
            self.stock_price = quote.get("price", "—")
            self.stock_change = quote.get("change", "—")
            self.stock_change_value = quote.get("change_value", "—")
            self.stock_change_pct = quote.get("change_pct", "")
            self.stock_change_is_positive = bool(quote.get("is_positive", True))
            self.stock_volume = quote.get("volume", "—")
            self.stock_market_cap = quote.get("market_cap", "—")
            self.stock_last_updated = last_updated
            self.stock_is_cached = is_cached
        except Exception:
            self.stock_error = "종목 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
            self.stock_is_cached = False
        finally:
            self.stock_loading = False

    async def load_liquidity_data(self):
        """FRED에서 유동성 지표를 불러옵니다 (1시간 TTL 캐시)."""
        self.liq_loading = True
        self.liq_error = ""
        try:
            from macro_wide.services.fred_data import get_liquidity_data, fmt_pct

            data, history, last_updated, is_cached = get_liquidity_data(ttl_seconds=3600)

            self.liq_fed_assets = data["fed_assets_str"]
            self.liq_fed_assets_change = fmt_pct(data["fed_assets_change"])
            self.liq_fed_assets_is_positive = data["fed_assets_change"] >= 0

            self.liq_tga_balance = data["tga_balance_str"]
            self.liq_tga_change = fmt_pct(data["tga_change"])
            # TGA 증가는 유동성 감소 → 부정적
            self.liq_tga_is_positive = data["tga_change"] <= 0

            self.liq_rrp_balance = data["rrp_balance_str"]
            self.liq_rrp_change = fmt_pct(data["rrp_change"])
            # RRP 증가는 유동성 감소 → 부정적
            self.liq_rrp_is_positive = data["rrp_change"] <= 0

            self.liq_net_liquidity = data["net_liquidity_str"]
            self.liq_net_liquidity_change = fmt_pct(data["net_liquidity_change"])
            self.liq_net_is_positive = data["net_liquidity_change"] >= 0

            self.liq_sp500 = data["sp500_str"]
            self.liq_sp500_change = fmt_pct(data["sp500_change"])
            self.liq_sp500_is_positive = data["sp500_change"] >= 0

            self.liq_history = list(history)
            self.liq_last_updated = last_updated
            self.liq_is_cached = is_cached
        except ValueError as e:
            # API 키 미설정 등
            self.liq_error = str(e)
            self.liq_is_cached = False
        except Exception:
            self.liq_error = "유동성 데이터를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
            self.liq_is_cached = False
        finally:
            self.liq_loading = False


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
                rx.link("경제지표", href="/indicators", class_name="text-gray-300 hover:text-emerald-400"),
                rx.link("주식분석", href="/stocks", class_name="text-gray-300 hover:text-emerald-400"),
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


def indicator_card(name: str, value: str, change: str, is_positive) -> rx.Component:
    """경제 지표 카드"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.text(name, class_name="text-gray-400 text-sm font-medium"),
                rx.cond(
                    is_positive,
                    rx.icon("trending-up", size=16, color="#10b981"),
                    rx.icon("trending-down", size=16, color="#ef4444"),
                ),
                justify="between",
                width="100%",
            ),
            rx.text(value, class_name="text-2xl font-bold text-white"),
            rx.cond(
                is_positive,
                rx.text(change, class_name="text-sm font-semibold text-emerald-400"),
                rx.text(change, class_name="text-sm font-semibold text-red-400"),
            ),
            align="start",
            spacing="2",
            width="100%",
        ),
        class_name="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 hover:border-emerald-500/50 transition-all cursor-pointer",
    )


def refresh_icon_button(*, on_click, disabled: bool) -> rx.Component:
    """'새로고침' 아이콘 버튼(텍스트 대신 이미지 사용)."""
    return rx.button(
        rx.image(
            src="/refresh.svg",
            alt="새로고침",
            class_name="w-4 h-4 opacity-80 group-hover:opacity-100 group-hover:brightness-150",
        ),
        size="1",
        variant="ghost",
        class_name="group p-2",
        on_click=on_click,
        disabled=disabled,
    )


def indicators_section() -> rx.Component:
    """경제 지표 섹션"""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("실시간 시장 지표", class_name="text-2xl font-bold text-white"),
                rx.hstack(
                    rx.cond(
                        State.last_updated != "",
                        rx.cond(
                            State.is_cached,
                            rx.text(
                                f"Updated: {State.last_updated} (cached)",
                                class_name="text-gray-500 text-xs",
                            ),
                            rx.text(
                                f"Updated: {State.last_updated}",
                                class_name="text-gray-500 text-xs",
                            ),
                        ),
                        rx.text("", class_name="text-gray-500 text-sm"),
                    ),
                    refresh_icon_button(on_click=State.load_indicators, disabled=State.loading),
                    spacing="3",
                    align="center",
                ),
                justify="between",
                align="center",
                width="100%",
                class_name="mb-6",
            ),
            rx.cond(
                State.error != "",
                rx.box(
                    rx.text(State.error, class_name="text-red-400 text-sm"),
                    class_name="mb-4",
                ),
                rx.box(),
            ),
            rx.box(
                rx.cond(
                    State.loading,
                    rx.box(
                        rx.text("Loading...", class_name="text-gray-400"),
                        class_name="py-6",
                    ),
                    rx.box(
                        rx.foreach(
                            State.indicators,
                            lambda ind: indicator_card(
                                ind["name"],
                                ind["value"],
                                ind["change"],
                                ind["is_positive"],
                            ),
                        ),
                        class_name="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 w-full",
                    ),
                ),
                class_name="w-full",
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


def page_layout(title: str, icon: str, description: str) -> rx.Component:
    """빈 페이지 레이아웃"""
    return rx.box(
        navbar(),
        rx.box(
            rx.vstack(
                rx.box(
                    rx.icon(icon, size=48, color="#10b981"),
                    class_name="w-24 h-24 bg-emerald-500/10 rounded-2xl flex items-center justify-center mb-6",
                ),
                rx.heading(
                    title,
                    class_name="text-3xl font-bold text-white mb-4",
                ),
                rx.text(
                    description,
                    class_name="text-gray-400 text-center max-w-md mb-8",
                ),
                rx.badge(
                    "Coming Soon",
                    class_name="bg-emerald-500/20 text-emerald-400 px-4 py-2 text-sm",
                ),
                align="center",
                justify="center",
                class_name="min-h-[60vh] pt-24",
            ),
            footer(),
            class_name="max-w-7xl mx-auto px-6",
        ),
        class_name="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950",
    )


def stock_list_item(stock) -> rx.Component:
    """좌측 종목 리스트 아이템"""
    is_selected = stock["symbol"] == State.selected_symbol
    base = rx.hstack(
        rx.vstack(
            rx.text(stock["name"], class_name="text-sm font-semibold text-white"),
            rx.hstack(
                rx.badge(stock["symbol"], class_name="bg-slate-700/60 text-gray-200 text-xs"),
                rx.text(stock["market"], class_name="text-xs text-gray-500"),
                spacing="2",
            ),
            spacing="2",
            align="start",
        ),
        justify="between",
        align="center",
        width="100%",
    )
    return rx.button(
        base,
        id=f"stock-{stock['symbol']}",
        width="100%",
        variant="ghost",
        class_name=rx.cond(
            is_selected,
            # 레이아웃 고정: 동일 padding + 동일 border 두께(transparent -> emerald로만 변경)
            "justify-start px-3 py-3 border border-emerald-500/30 bg-emerald-500/15 hover:bg-emerald-500/20 ring-1 ring-inset ring-emerald-500/20",
            "justify-start px-3 py-3 border border-transparent hover:bg-slate-800/60",
        ),
        on_click=State.set_selected_symbol(stock["symbol"]),
    )


def stocks_layout() -> rx.Component:
    """주식분석: 좌측 리스트 + 우측 상세"""
    return rx.box(
        # 5분 주기로 데이터 갱신(메인 '실시간 시장 지표'와 동일한 TTL=300s에 맞춤)
        # - 선택 종목은 localStorage로 저장/복원하여 리로드 시에도 유지합니다.
        rx.script(
            """
(function () {
  if (typeof window === 'undefined') return;

  // Store selected symbol on click.
  if (!window.__macrowide_stock_sel_listener) {
    window.__macrowide_stock_sel_listener = true;
    document.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest ? e.target.closest('button[id^="stock-"]') : null;
      if (!btn || !btn.id) return;
      var sym = btn.id.replace('stock-', '');
      try { window.localStorage.setItem('macrowide_selected_symbol', sym); } catch (_) {}
    }, true);
  }

  // Restore selection after mount.
  if (!window.__macrowide_stock_sel_restore) {
    window.__macrowide_stock_sel_restore = true;
    setTimeout(function () {
      var sym = null;
      try { sym = window.localStorage.getItem('macrowide_selected_symbol'); } catch (_) {}
      if (!sym) return;
      var btn = document.getElementById('stock-' + sym);
      if (btn) btn.click();
    }, 100);
  }

  // Auto refresh every 5 minutes.
  if (window.__macrowide_stocks_autorefresh) return;
  window.__macrowide_stocks_autorefresh = setInterval(function () {
    window.location.reload();
  }, 300000);
})();
            """.strip()
        ),
        navbar(),
        rx.box(
            rx.box(
                rx.heading("주식분석", class_name="text-2xl font-bold text-white"),
                rx.text(
                    "좌측에서 종목을 선택하면 우측에서 상세 내용을 확인할 수 있습니다.",
                    class_name="text-gray-400 text-sm",
                ),
                class_name="pt-24 mb-6",
            ),
            rx.box(
                # Sidebar (mobile: top, desktop: left)
                rx.box(
                    rx.vstack(
                        rx.input(
                            placeholder="Search (symbol or name)",
                            value=State.stock_query,
                            on_change=State.set_stock_query,
                            class_name="bg-slate-900/60 border border-slate-700/60 text-gray-200 placeholder:text-gray-500",
                        ),
                        rx.box(
                            rx.foreach(State.filtered_stocks, stock_list_item),
                            class_name="w-full flex flex-col gap-2 overflow-auto max-h-64 md:max-h-[70vh] pr-1",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    class_name="w-full md:w-65 md:min-w-65 bg-slate-800/30 border border-slate-700/50 rounded-xl p-4",
                ),
                # Detail pane
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.heading(State.selected_stock["name"], class_name="text-xl font-bold text-white"),
                            rx.badge(
                                State.selected_stock["symbol"],
                                class_name="bg-emerald-500/20 text-emerald-300",
                            ),
                            rx.badge(
                                State.selected_stock["market"],
                                class_name="bg-slate-700/50 text-gray-300",
                            ),
                            spacing="2",
                            align="center",
                            flex_wrap="wrap",
                        ),
                        rx.text(
                            "여기에 종목 개요, 현재가/등락, 차트, 주요 재무 지표 등을 순차적으로 추가할 예정입니다.",
                            class_name="text-gray-400 text-sm",
                        ),
                        rx.hstack(
                            rx.cond(
                                State.stock_last_updated != "",
                                rx.cond(
                                    State.stock_is_cached,
                                    rx.text(
                                        f"Updated: {State.stock_last_updated} (cached)",
                                        class_name="text-gray-500 text-xs",
                                    ),
                                    rx.text(
                                        f"Updated: {State.stock_last_updated}",
                                        class_name="text-gray-500 text-xs",
                                    ),
                                ),
                                rx.text("", class_name="text-gray-500 text-sm"),
                            ),
                            refresh_icon_button(on_click=State.load_stock_quote, disabled=State.stock_loading),
                            spacing="3",
                            align="center",
                            width="100%",
                            class_name="mt-1",
                            justify="end",
                        ),
                        rx.cond(
                            State.stock_error != "",
                            rx.box(
                                rx.text(State.stock_error, class_name="text-red-400 text-sm"),
                                class_name="mt-2",
                            ),
                            rx.box(),
                        ),
                        rx.box(
                            rx.hstack(
                                rx.box(
                                    rx.text("현재가", class_name="text-xs text-gray-500"),
                                    rx.text(State.stock_price, class_name="text-lg font-semibold text-white"),
                                    class_name="flex-1 bg-slate-900/40 border border-slate-700/50 rounded-lg p-4",
                                ),
                                rx.box(
                                    rx.text("등락", class_name="text-xs text-gray-500"),
                                    rx.hstack(
                                        rx.text(
                                            State.stock_change_value,
                                            class_name="text-lg font-semibold text-white whitespace-nowrap",
                                        ),
                                        rx.cond(
                                            State.stock_change_pct != "",
                                            rx.text(
                                                State.stock_change_pct,
                                                class_name="text-sm font-semibold text-white/70 whitespace-nowrap",
                                            ),
                                            rx.box(),
                                        ),
                                        spacing="2",
                                        class_name="items-baseline flex-nowrap",
                                    ),
                                    class_name="flex-1 bg-slate-900/40 border border-slate-700/50 rounded-lg p-4",
                                ),
                                rx.box(
                                    rx.text("거래량", class_name="text-xs text-gray-500"),
                                    rx.text(State.stock_volume, class_name="text-lg font-semibold text-white"),
                                    class_name="flex-1 bg-slate-900/40 border border-slate-700/50 rounded-lg p-4",
                                ),
                                rx.box(
                                    rx.text("시총", class_name="text-xs text-gray-500"),
                                    rx.text(State.stock_market_cap, class_name="text-lg font-semibold text-white"),
                                    class_name="flex-1 bg-slate-900/40 border border-slate-700/50 rounded-lg p-4",
                                ),
                                spacing="4",
                                width="100%",
                                class_name="flex-col md:flex-row",
                            ),
                            width="100%",
                        ),
                        rx.box(
                            rx.badge(
                                "Coming Soon",
                                class_name="bg-emerald-500/20 text-emerald-400 px-3 py-1 text-sm",
                            ),
                            class_name="mt-2",
                        ),
                        spacing="4",
                        align="start",
                        width="100%",
                    ),
                    class_name="flex-1 bg-slate-800/30 border border-slate-700/50 rounded-xl p-6",
                ),
                class_name="flex flex-col md:flex-row gap-6",
            ),
            footer(),
            class_name="max-w-7xl mx-auto px-6",
        ),
        class_name="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950",
    )


def index() -> rx.Component:
    """메인 페이지"""
    return rx.box(
        # 5분 주기로 자동 새로고침(키 없는 무료 데이터 소스의 TTL과 동일)
        rx.script(
            """
(function () {
  if (typeof window === 'undefined') return;
  if (window.__macrowide_autorefresh) return;
  window.__macrowide_autorefresh = setInterval(function () {
    window.location.reload();
  }, 300000);
})();
            """.strip()
        ),
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


def stocks_page() -> rx.Component:
    """주식분석 페이지"""
    return stocks_layout()


def liquidity_card(
    title: str,
    value,
    change,
    is_positive,
    icon_name: str,
    color: str,
    description: str = "",
) -> rx.Component:
    """유동성 지표 카드 컴포넌트.

    Args:
        title: 카드 제목
        value: 현재 값 (State 변수)
        change: 변화율 (State 변수)
        is_positive: 긍정적 변화 여부 (State 변수)
        icon_name: Lucide 아이콘 이름
        color: 테마 색상 (emerald, red, orange, blue)
        description: 설명 텍스트
    """
    color_map = {
        "emerald": {
            "bg": "bg-emerald-500/10",
            "border": "border-emerald-500/30",
            "icon": "#10b981",
            "text": "text-emerald-400",
        },
        "red": {
            "bg": "bg-red-500/10",
            "border": "border-red-500/30",
            "icon": "#ef4444",
            "text": "text-red-400",
        },
        "orange": {
            "bg": "bg-orange-500/10",
            "border": "border-orange-500/30",
            "icon": "#f97316",
            "text": "text-orange-400",
        },
        "blue": {
            "bg": "bg-blue-500/10",
            "border": "border-blue-500/30",
            "icon": "#3b82f6",
            "text": "text-blue-400",
        },
        "purple": {
            "bg": "bg-purple-500/10",
            "border": "border-purple-500/30",
            "icon": "#a855f7",
            "text": "text-purple-400",
        },
    }
    c = color_map.get(color, color_map["emerald"])

    # description이 있으면 표시, 없으면 빈 box
    desc_element = (
        rx.text(description, class_name="text-gray-500 text-xs")
        if description
        else rx.box()
    )

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.box(
                    rx.icon(icon_name, size=24, color=c["icon"]),
                    class_name=f"w-12 h-12 {c['bg']} rounded-xl flex items-center justify-center",
                ),
                rx.vstack(
                    rx.text(title, class_name="text-gray-400 text-sm font-medium"),
                    desc_element,
                    spacing="1",
                    align="start",
                ),
                spacing="3",
                align="center",
                width="100%",
            ),
            rx.text(value, class_name="text-3xl font-bold text-white mt-2"),
            rx.hstack(
                rx.cond(
                    is_positive,
                    rx.hstack(
                        rx.icon("trending-up", size=16, color="#10b981"),
                        rx.text(change, class_name="text-sm font-semibold text-emerald-400"),
                        spacing="1",
                        align="center",
                    ),
                    rx.hstack(
                        rx.icon("trending-down", size=16, color="#ef4444"),
                        rx.text(change, class_name="text-sm font-semibold text-red-400"),
                        spacing="1",
                        align="center",
                    ),
                ),
                rx.text("vs 전주", class_name="text-xs text-gray-500"),
                spacing="2",
                align="center",
            ),
            align="start",
            spacing="2",
            width="100%",
        ),
        class_name=f"bg-slate-800/50 border {c['border']} rounded-xl p-5 hover:border-opacity-60 transition-all",
    )


def liquidity_pipeline() -> rx.Component:
    """유동성 파이프라인 시각화 (Sankey 스타일 흐름도)."""
    return rx.box(
        rx.vstack(
            rx.heading("유동성 파이프라인", class_name="text-xl font-bold text-white mb-2"),
            rx.text(
                "연준 총자산에서 TGA와 RRP를 차감하면 시중 순유동성이 됩니다.",
                class_name="text-gray-400 text-sm mb-6",
            ),
            # 파이프라인 흐름도
            rx.box(
                rx.hstack(
                    # 공급: Fed Balance Sheet
                    rx.box(
                        rx.vstack(
                            rx.text("📊 공급", class_name="text-xs text-emerald-400 font-semibold"),
                            rx.text("Fed Balance Sheet", class_name="text-sm text-gray-300"),
                            rx.text(State.liq_fed_assets, class_name="text-2xl font-bold text-emerald-400"),
                            rx.text(State.liq_fed_assets_change, class_name="text-xs text-gray-400"),
                            spacing="1",
                            align="center",
                        ),
                        class_name="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 flex-1",
                    ),
                    # 화살표
                    rx.box(
                        rx.icon("arrow-right", size=24, color="#6b7280"),
                        class_name="flex items-center px-2",
                    ),
                    # 차감: TGA + RRP
                    rx.box(
                        rx.vstack(
                            rx.text("🚰 차감", class_name="text-xs text-red-400 font-semibold"),
                            rx.hstack(
                                rx.vstack(
                                    rx.text("TGA", class_name="text-xs text-gray-400"),
                                    rx.text(State.liq_tga_balance, class_name="text-lg font-bold text-red-400"),
                                    spacing="0",
                                    align="center",
                                ),
                                rx.text("+", class_name="text-gray-500 text-xl font-bold"),
                                rx.vstack(
                                    rx.text("RRP", class_name="text-xs text-gray-400"),
                                    rx.text(State.liq_rrp_balance, class_name="text-lg font-bold text-orange-400"),
                                    spacing="0",
                                    align="center",
                                ),
                                spacing="3",
                                align="center",
                            ),
                            spacing="2",
                            align="center",
                        ),
                        class_name="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex-1",
                    ),
                    # 화살표
                    rx.box(
                        rx.icon("arrow-right", size=24, color="#6b7280"),
                        class_name="flex items-center px-2",
                    ),
                    # 결과: Net Liquidity
                    rx.box(
                        rx.vstack(
                            rx.text("💧 순유동성", class_name="text-xs text-blue-400 font-semibold"),
                            rx.text("Net Liquidity", class_name="text-sm text-gray-300"),
                            rx.text(State.liq_net_liquidity, class_name="text-2xl font-bold text-blue-400"),
                            rx.text(State.liq_net_liquidity_change, class_name="text-xs text-gray-400"),
                            spacing="1",
                            align="center",
                        ),
                        class_name="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 flex-1",
                    ),
                    spacing="2",
                    width="100%",
                    class_name="flex-col md:flex-row",
                ),
                width="100%",
            ),
            # 공식 설명
            rx.box(
                rx.text(
                    "Net Liquidity = WALCL − (WDTGAL + RRPONTSYD)",
                    class_name="text-xs text-gray-500 font-mono text-center",
                ),
                class_name="mt-4 p-2 bg-slate-900/50 rounded-lg",
            ),
            width="100%",
            align="start",
        ),
        class_name="bg-slate-800/30 border border-slate-700/50 rounded-xl p-6",
    )


def liquidity_chart() -> rx.Component:
    """유동성 vs S&P 500 상관관계 차트."""
    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.heading("유동성 vs S&P 500", class_name="text-xl font-bold text-white"),
                rx.badge("상관관계", class_name="bg-purple-500/20 text-purple-400"),
                spacing="3",
                align="center",
            ),
            rx.text(
                "순유동성과 S&P 500 지수의 역사적 상관관계를 확인하세요.",
                class_name="text-gray-400 text-sm mb-4",
            ),
            # Plotly 차트
            rx.box(
                rx.plotly(data=State.liquidity_chart_figure),
                class_name="w-full h-96",
            ),
            width="100%",
            align="start",
        ),
        class_name="bg-slate-800/30 border border-slate-700/50 rounded-xl p-6",
    )


def indicators_page() -> rx.Component:
    """경제지표 페이지 - 미국 유동성 대시보드."""
    return rx.box(
        navbar(),
        rx.box(
            # 헤더 섹션
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.hstack(
                            rx.icon("droplets", size=32, color="#3b82f6"),
                            rx.heading("미국 유동성 대시보드", class_name="text-2xl font-bold text-white"),
                            spacing="3",
                            align="center",
                        ),
                        rx.text(
                            "연준 자산, TGA, 역레포를 추적하여 시중 유동성을 모니터링합니다.",
                            class_name="text-gray-400 text-sm",
                        ),
                        spacing="2",
                        align="start",
                    ),
                    rx.hstack(
                        rx.cond(
                            State.liq_last_updated != "",
                            rx.cond(
                                State.liq_is_cached,
                                rx.text(
                                    f"Updated: {State.liq_last_updated} (cached)",
                                    class_name="text-gray-500 text-xs",
                                ),
                                rx.text(
                                    f"Updated: {State.liq_last_updated}",
                                    class_name="text-gray-500 text-xs",
                                ),
                            ),
                            rx.text("", class_name="text-gray-500 text-sm"),
                        ),
                        refresh_icon_button(on_click=State.load_liquidity_data, disabled=State.liq_loading),
                        spacing="3",
                        align="center",
                    ),
                    justify="between",
                    align="center",
                    width="100%",
                    class_name="flex-col md:flex-row gap-4",
                ),
                class_name="pt-24 mb-8",
            ),
            # 에러 메시지
            rx.cond(
                State.liq_error != "",
                rx.box(
                    rx.hstack(
                        rx.icon("alert-circle", size=18, color="#ef4444"),
                        rx.text(State.liq_error, class_name="text-red-400 text-sm"),
                        spacing="2",
                        align="center",
                    ),
                    class_name="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6",
                ),
                rx.box(),
            ),
            # 로딩 상태
            rx.cond(
                State.liq_loading,
                rx.box(
                    rx.hstack(
                        rx.icon("loader-2", size=24, color="#6b7280", class_name="animate-spin"),
                        rx.text("데이터를 불러오는 중...", class_name="text-gray-400"),
                        spacing="3",
                        align="center",
                        justify="center",
                    ),
                    class_name="py-12",
                ),
                rx.vstack(
                    # 상단: 지표 카드들
                    rx.box(
                        rx.hstack(
                            liquidity_card(
                                title="Fed Balance Sheet",
                                value=State.liq_fed_assets,
                                change=State.liq_fed_assets_change,
                                is_positive=State.liq_fed_assets_is_positive,
                                icon_name="landmark",
                                color="emerald",
                                description="연준 총자산 (WALCL)",
                            ),
                            liquidity_card(
                                title="TGA (재무부 계정)",
                                value=State.liq_tga_balance,
                                change=State.liq_tga_change,
                                is_positive=State.liq_tga_is_positive,
                                icon_name="piggy-bank",
                                color="red",
                                description="Treasury General Account",
                            ),
                            liquidity_card(
                                title="RRP (역레포)",
                                value=State.liq_rrp_balance,
                                change=State.liq_rrp_change,
                                is_positive=State.liq_rrp_is_positive,
                                icon_name="rotate-ccw",
                                color="orange",
                                description="Reverse Repo Facility",
                            ),
                            liquidity_card(
                                title="Net Liquidity",
                                value=State.liq_net_liquidity,
                                change=State.liq_net_liquidity_change,
                                is_positive=State.liq_net_is_positive,
                                icon_name="droplets",
                                color="blue",
                                description="순유동성",
                            ),
                            liquidity_card(
                                title="S&P 500",
                                value=State.liq_sp500,
                                change=State.liq_sp500_change,
                                is_positive=State.liq_sp500_is_positive,
                                icon_name="trending-up",
                                color="purple",
                                description="주식시장 지표",
                            ),
                            spacing="4",
                            width="100%",
                            class_name="flex-col lg:flex-row",
                        ),
                        class_name="mb-8",
                    ),
                    # 중단: 유동성 파이프라인
                    rx.box(
                        liquidity_pipeline(),
                        class_name="mb-8 w-full",
                    ),
                    # 하단: 상관관계 차트
                    rx.box(
                        liquidity_chart(),
                        class_name="w-full",
                    ),
                    width="100%",
                    spacing="0",
                ),
            ),
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
app.add_page(index, title="MacroWide - 글로벌 경제 대시보드", on_load=State.load_indicators)
app.add_page(stocks_page, route="/stocks", title="MacroWide - 주식분석", on_load=State.load_stock_quote)
app.add_page(
    indicators_page,
    route="/indicators",
    title="MacroWide - 미국 유동성 대시보드",
    on_load=State.load_liquidity_data,
)
