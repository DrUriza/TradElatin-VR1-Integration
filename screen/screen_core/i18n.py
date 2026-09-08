from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import re
from typing import Any
from urllib.parse import parse_qs

SUPPORTED_LOCALES = ("en", "es")
DEFAULT_LOCALE = "en"

# UI phrases only. Technical identifiers such as CVD, VWAP, RSI, DVOL,
# Open Interest, Funding, Spot, Perpetual and Wasserstein remain canonical.
_PAIRS: tuple[tuple[str, str], ...] = (
    ("Prices", "Precios"),
    ("ETF Flows", "Flujos ETF"),
    ("Liquidity", "Liquidez"),
    ("Liquidations", "Liquidaciones"),
    ("On-Chain Miners", "On-Chain y Mineros"),
    ("Volatility", "Volatilidad"),
    ("SCREEN A", "PANTALLA A"),
    ("SCREEN B", "PANTALLA B"),
    ("REFERENCE", "REFERENCIA"),
    ("CONTRACT REFERENCE", "REFERENCIA CONTRACTUAL"),
    ("TRAD ELATIN TRADING TOOL", "TRAD ELATIN · HERRAMIENTA DE TRADING"),
    ("FUNDAMENTAL TECHNICAL ANALYSIS", "ANÁLISIS TÉCNICO FUNDAMENTAL"),
    ("VIEW", "VISTA"),
    ("MARKET", "MERCADO"),
    ("TIMEFRAME", "TEMPORALIDAD"),
    ("LANGUAGE", "IDIOMA"),
    ("RELOAD", "RECARGAR"),
    ("UPDATING", "ACTUALIZANDO"),
    ("REFRESH TIMEOUT", "TIEMPO DE ACTUALIZACIÓN AGOTADO"),
    ("EXCHANGE", "EXCHANGE"),
    ("LONG / SHORT RATIO", "RATIO LONG / SHORT"),
    ("SPOT FLOW", "FLUJO SPOT"),
    ("FUTURES FLOW", "FLUJO FUTURES"),
    ("PERPETUAL FLOW", "FLUJO PERPETUO"),
    ("FUTURES / PERPETUAL FLOW", "FLUJO FUTURES / PERPETUO"),
    ("BUY FLOW", "FLUJO COMPRADOR"),
    ("SELL FLOW", "FLUJO VENDEDOR"),
    ("NET FLOW HISTORY", "HISTÓRICO DE FLUJO NETO"),
    ("HISTORY —", "HISTÓRICO —"),
    ("DATA AS OF", "DATOS AL"),
    ("DATA SOURCE STATUS", "ESTADO DE FUENTES DE DATOS"),
    ("JSON contracts loaded from data/contracts", "Contratos JSON cargados desde data/contracts"),
    ("HMI computes no market indicators", "La HMI no calcula indicadores de mercado"),
    ("TradELATIN VR1 · Screen Deployment", "TradELATIN VR1 · Despliegue HMI"),
    ("BACK", "REGRESAR"),
    ("← BACK", "← REGRESAR"),
    ("AVAILABLE", "DISPONIBLE"),
    ("UNAVAILABLE", "NO DISPONIBLE"),
    ("PARTIAL", "PARCIAL"),
    ("WARNING", "ADVERTENCIA"),
    ("ERROR", "ERROR"),
    ("NORMAL", "NORMAL"),
    ("POSITIVE", "POSITIVO"),
    ("NEGATIVE", "NEGATIVO"),
    ("BULLISH", "ALCISTA"),
    ("BEARISH", "BAJISTA"),
    ("NEUTRAL", "NEUTRAL"),
    ("BUYING", "COMPRADOR"),
    ("SELLING", "VENDEDOR"),
    ("EXPANDING", "EXPANSIÓN"),
    ("DEGRADED", "DEGRADADO"),
    ("MIXED", "MIXTO"),
    ("ESTIMATED", "ESTIMADO"),
    ("SYNTHETIC", "SINTÉTICO"),
    ("DATA QUALITY", "CALIDAD DE DATOS"),
    ("SIGNAL", "SEÑAL"),
    ("INDICATORS", "INDICADORES"),
    ("INDICATOR SUMMARY", "RESUMEN DE INDICADORES"),
    ("INDICATOR", "INDICADOR"),
    ("VALUE", "VALOR"),
    ("STRENGTH", "FUERZA"),
    ("STRENGTH LEGEND", "LEYENDA DE FUERZA"),
    ("VERY STRONG", "MUY FUERTE"),
    ("STRONG", "FUERTE"),
    ("MODERATE", "MODERADA"),
    ("WEAK", "DÉBIL"),
    ("VERY WEAK", "MUY DÉBIL"),
    ("CHANGE 24H", "CAMBIO 24H"),
    ("VOLUME 24H", "VOLUMEN 24H"),
    ("VOLUME", "VOLUMEN"),
    ("INDICATORS", "INDICADORES"),
    ("(Select to display)", "(Selecciona para mostrar)"),
    ("BANDS, LEVELS & CHANNELS · ON PRICE", "BANDAS, NIVELES Y CANALES · SOBRE PRECIO"),
    ("Support", "Soporte"),
    ("Resistance", "Resistencia"),
    ("Price (USDT)", "Precio (USDT)"),
    ("Cumulative (BTC)", "Acumulado (BTC)"),
    ("HISTOGRAM", "HISTOGRAMA"),
    ("Buy Share", "Participación compradora"),
    ("BUY DOMINANT", "DOMINIO COMPRADOR"),
    ("SELL DOMINANT", "DOMINIO VENDEDOR"),
    ("FUTURES DOMINANT", "DOMINIO FUTUROS"),
    ("STABLE", "ESTABLE"),
    ("POSITIVE SLOPE", "PENDIENTE +"),
    ("NEGATIVE SLOPE", "PENDIENTE -"),
    ("BUY PRESSURE", "PRESIÓN COMPRA"),
    ("SELL PRESSURE", "PRESIÓN VENTA"),
    ("CVD > PRICE", "CVD > PRECIO"),
    ("OI ROC / SLOPE / ACCELERATION", "OI ROC / PENDIENTE / ACELERACIÓN"),
    ("OI Z-SCORE / PERCENTILE", "OI Z-SCORE / PERCENTIL"),
    ("PRICE × OPEN INTEREST REGIME", "PRECIO × RÉGIMEN DE OPEN INTEREST"),
    ("PRICE ↔ OPEN INTEREST DIVERGENCE", "PRECIO ↔ DIVERGENCIA DE OPEN INTEREST"),
    ("FUNDING × OPEN INTEREST CROWDING", "FUNDING × CONCENTRACIÓN DE OPEN INTEREST"),
    ("WASSERSTEIN / REGIME SHIFT", "WASSERSTEIN / CAMBIO DE RÉGIMEN"),
    ("ACCEL %", "ACEL. %"),
    ("DIVERGENCE", "DIVERGENCIA"),
    ("LONG CROWDING", "CONCENTRACIÓN LONG"),
    ("LONG DELEVERAGING", "DESAPALANCAMIENTO LONG"),
    ("REGIME SCORE", "PUNTAJE DE RÉGIMEN"),
    ("SLOPE %", "PENDIENTE %"),
    ("long_liquidation", "liquidación long"),
    ("BALANCED", "EQUILIBRADO"),
    ("ELEVATED PROFITABILITY", "RENTABILIDAD ELEVADA"),
    ("HASH RECOVERY", "RECUPERACIÓN DE HASHRATE"),
    ("MINER ECONOMICS", "ECONOMÍA MINERA"),
    ("MINER REGIME", "RÉGIMEN DE MINEROS"),
    ("MINER TREASURY", "TESORERÍA DE MINEROS"),
    ("NETWORK HEALTH", "SALUD DE RED"),
    ("NETWORK STRESS", "ESTRÉS DE RED"),
    ("RECOVERY", "RECUPERACIÓN"),
    ("SELLING PRESSURE", "PRESIÓN DE VENTA"),
    ("OPTIONS STRUCTURE · IV TERM STRUCTURE / SLOPE", "ESTRUCTURA DE OPCIONES · ESTRUCTURA TEMPORAL IV / PENDIENTE"),
    ("OPTIONS STRUCTURE · VOLATILITY SKEW / TAIL RISK", "ESTRUCTURA DE OPCIONES · SKEW DE VOLATILIDAD / RIESGO DE COLA"),
    ("REGIME · REGIME SHIFT / WASSERSTEIN", "RÉGIMEN · CAMBIO DE RÉGIMEN / WASSERSTEIN"),
    ("VOLATILITY DYNAMICS · VOL-OF-VOL / ACCELERATION", "DINÁMICA DE VOLATILIDAD · VOL-OF-VOL / ACELERACIÓN"),
    ("VOLATILITY LEVEL · VOLATILITY Z-SCORE / PERCENTILE", "NIVEL DE VOLATILIDAD · Z-SCORE / PERCENTIL"),
    ("VOLATILITY PRICING · VOLATILITY RISK PREMIUM", "PRECIO DE VOLATILIDAD · PRIMA DE RIESGO DE VOLATILIDAD"),
    ("Buy Total", "Total comprador"),
    ("Sell Total", "Total vendedor"),
    ("Distance", "Distancia"),
    ("Notional (USD)", "Nocional (USD)"),
    ("Side", "Lado"),
    ("Time", "Hora"),
    ("Total Asks", "Total Ask"),
    ("Total Bids", "Total Bid"),
    ("DEPTH IMBALANCE", "DESEQUILIBRIO DE PROFUNDIDAD"),
    ("LIQUIDITY STRESS", "ESTRÉS DE LIQUIDEZ"),
    ("ABSORPTION", "ABSORCIÓN"),
    ("Volume", "Volumen"),
    ("They are not overlaid on or used to modify the candle reading.", "No se superponen ni se usan para modificar la lectura de las velas."),
    ("MOMENTUM", "IMPULSO"),
    ("VOLATILITY", "VOLATILIDAD"),
    ("CROWDING", "CONCENTRACIÓN"),
    ("PERCENTILE", "PERCENTIL"),
    ("PRICE Z", "PRECIO Z"),
    ("NEUTRAL / MIXED", "NEUTRAL / MIXTO"),
    ("Capitulation", "Capitulación"),
    ("Capitulation %", "Capitulación %"),
    ("Recovery %", "Recuperación %"),
    ("SHORTS", "CORTOS"),
    ("SELL", "VENTA"),
    ("REGIME", "RÉGIMEN"),
    ("FLOW", "FLUJO"),
    ("BTC (Cumulative)", "BTC (Acumulado)"),
    ("BUY / SELL VOLUME", "VOLUMEN COMPRA / VENTA"),
    ("BUY", "COMPRA"),
    ("SELL", "VENTA"),
    ("BANDS & CHANNELS · ON OPEN INTEREST", "BANDAS Y CANALES · SOBRE OPEN INTEREST"),
    ("No indicators selected for Screen B.", "No seleccionaste indicadores para la Pantalla B."),
    ("TREND · ON CVD", "TENDENCIA · SOBRE CVD"),
    ("FLOW DYNAMICS", "DINÁMICA DEL FLUJO"),
    ("DIVERGENCES", "DIVERGENCIAS"),
    ("REGIME CHANGE", "CAMBIO DE RÉGIMEN"),
    ("SUMMARY · CVD SPOT", "RESUMEN · CVD SPOT"),
    ("SUMMARY · CVD FUTURES", "RESUMEN · CVD FUTURES"),
    ("FLOW & CAPITAL ANALYSIS", "ANÁLISIS DE FLUJOS Y CAPITAL"),
    ("FLOW & CAPITAL SUMMARY", "RESUMEN DE FLUJOS Y CAPITAL"),
    ("METRIC", "MÉTRICA"),
    ("STATE", "ESTADO"),
    ("MIXED FLOW", "FLUJO MIXTO"),
    ("NORMAL FLOW", "FLUJO NORMAL"),
    ("FLOW MOMENTUM", "MOMENTUM DE FLUJO"),
    ("ETF FLOW Z", "Z DE FLUJO ETF"),
    ("PRICE CONFIRMATION", "CONFIRMACIÓN DE PRECIO"),
    ("PRICE LEADS ETF", "PRECIO LIDERA AL ETF"),
    ("FLOW PRESSURE", "PRESIÓN DE FLUJO"),
    ("BALANCED FLOW", "FLUJO BALANCEADO"),
    ("INSTITUTIONAL FLOW", "FLUJO INSTITUCIONAL"),
    ("EXCHANGE CAPITAL", "CAPITAL EN EXCHANGES"),
    ("CAPITAL REGIME", "RÉGIMEN DE CAPITAL"),
    ("NATIVE METRICS", "MÉTRICAS NATIVAS"),
    ("TREND", "TENDENCIA"),
    ("PARTICIPATION DYNAMICS", "DINÁMICA DE PARTICIPACIÓN"),
    ("PRICE × PARTICIPATION", "PRICE × PARTICIPACIÓN"),
    ("DISTRIBUTION & FLOW", "DISTRIBUCIÓN Y FLUJO"),
    ("ANALYSIS", "ANÁLISIS"),
    ("Size (BTC)", "Tamaño (BTC)"),
    ("Native capital-flow analytics. The HMI only plots metrics precomputed by Processing; it does not apply RSI/MACD/ATR or moving averages to reserves or flows.", "Analítica nativa de movimiento de capital. La HMI sólo grafica métricas precomputadas por Processing; no aplica RSI/MACD/ATR ni medias móviles a reservas o flujos."),
    ("No indicators selected for analysis on Screen A.", "No seleccionaste indicadores de análisis en Pantalla A."),
    ("REGRESSION CHANNEL", "CANAL DE REGRESIÓN"),
    ("BULLISH EXPANSION", "EXPANSIÓN ALCISTA"),
    ("BEARISH EXPANSION", "EXPANSIÓN BAJISTA"),
    ("CONTRACTING", "CONTRACCIÓN"),
    ("CONFIRMATION", "CONFIRMACIÓN"),
    ("Based on the indicator direction and current relative strength.", "Basado en la dirección del indicador y la fuerza relativa actual."),
    ("Values can change with the next candle close.", "Los valores pueden cambiar con el próximo cierre de vela."),
    ("HIGH 24H", "MÁX. 24H"),
    ("LOW 24H", "MÍN. 24H"),
    ("STOCHASTIC (14,3,3)", "ESTOCÁSTICO (14,3,3)"),
    ("Select to display", "Selecciona para mostrar"),
    ("Select indicators and open the analysis screen.", "Selecciona indicadores y abre la pantalla de análisis."),
    ("Open analysis in a new tab", "Abrir análisis en una nueva pestaña"),
    ("No indicators selected for Screen B.", "No seleccionaste indicadores para la Pantalla B."),
    ("No metrics selected for Screen B.", "No seleccionaste métricas para la Pantalla B."),
    ("No precomputed indicator block in JSON", "No existe un bloque de indicador precomputado en el JSON"),
    ("No KPI items in JSON", "No hay KPIs en el JSON"),
    ("No widget values are present", "No hay valores de widgets disponibles"),
    ("No rows in JSON", "No hay filas en el JSON"),
    ("Table missing in JSON", "La tabla no existe en el JSON"),
    ("No tabular rows in this contract section", "No hay filas tabulares en esta sección del contrato"),
    ("CONTRACT NOTE", "NOTA DEL CONTRATO"),
    ("CONTRACT LOAD ERROR", "ERROR AL CARGAR EL CONTRATO"),
    ("Correct the JSON and press RELOAD. No fallback data is fabricated.", "Corrige el JSON y presiona RECARGAR. La HMI no fabrica datos de respaldo."),
    ("WHAT IT MEASURES", "QUÉ MIDE"),
    ("PRICE RELATION", "RELACIÓN CON EL PRECIO"),
    ("CROSS-FAMILY RELATION", "RELACIÓN ENTRE FAMILIAS"),
    ("INTERPRETATION", "INTERPRETACIÓN"),
    ("VARIABLE TYPE", "TIPO DE VARIABLE"),
    ("RAW", "RAW"),
    ("PROCESSING", "PROCESSING"),
    ("CLASSIFICATION", "CLASSIFICATION"),
    ("DISPLAY", "VISUALIZACIÓN"),
    ("REFERENCE PRICE", "PRECIO DE REFERENCIA"),
    ("CURRENT PRICE", "PRECIO ACTUAL"),
    ("MID PRICE", "PRECIO MEDIO"),
    ("ORDER BOOK", "LIBRO DE ÓRDENES"),
    ("WHALE ORDERS", "ÓRDENES BALLENA"),
    ("LARGE TRADES", "OPERACIONES GRANDES"),
    ("EXECUTED LIQUIDITY / OPERATIONS", "LIQUIDEZ EJECUTADA / OPERACIONES"),
    ("ETF Daily Net Flow", "Flujo Neto Diario ETF"),
    ("ETF Flow by Provider", "Flujo ETF por Proveedor"),
    ("Exchange Net Flow", "Flujo Neto de Exchanges"),
    ("Exchange Balance / Reserve", "Balance / Reserva de Exchanges"),
    ("Miner Net Position Change", "Cambio Neto de Posición de Mineros"),
    ("Aggregated aggressive execution interacting with available liquidity", "Ejecución agresiva agregada interactuando con la liquidez disponible"),
    ("Accumulated order-book depth", "Profundidad acumulada del libro"),
    ("Large resting orders and associated liquidity", "Órdenes grandes en reposo y liquidez asociada"),
    ("Large executed trades and consumed liquidity", "Operaciones grandes ejecutadas y liquidez consumida"),
    ("CVD ANALYSIS · ORDER FLOW", "ANÁLISIS CVD · ORDER FLOW"),
    ("FLOW DYNAMICS · SCREEN B", "DINÁMICA DEL FLUJO · PANTALLA B"),
    ("DIVERGENCES · SCREEN B", "DIVERGENCIAS · PANTALLA B"),
    ("REGIME CHANGE · SCREEN B", "CAMBIO DE RÉGIMEN · PANTALLA B"),
    ("DERIVED ANALYSIS · SCREEN B", "ANÁLISIS DERIVADO · PANTALLA B"),
    ("MOMENTUM · SCREEN B", "MOMENTUM · PANTALLA B"),
    ("VOLATILITY · SCREEN B", "VOLATILIDAD · PANTALLA B"),
    ("PARTICIPATION DYNAMICS · SCREEN B", "DINÁMICA DE PARTICIPACIÓN · PANTALLA B"),
    ("PRICE × PARTICIPATION · SCREEN B", "PRICE × PARTICIPACIÓN · PANTALLA B"),
    ("LEVERAGE / REGIME CHANGE · SCREEN B", "LEVERAGE / CAMBIO DE RÉGIMEN · PANTALLA B"),
    ("ETF & EXCHANGE FLOWS · SCREEN B", "ETF & EXCHANGE FLOWS · PANTALLA B"),
    ("INSTITUTIONAL FLOW · SCREEN B", "FLUJO INSTITUCIONAL · PANTALLA B"),
    ("PRICE & EXCHANGE CAPITAL · SCREEN B", "PRICE & CAPITAL EN EXCHANGES · PANTALLA B"),
    ("CAPITAL REGIME · SCREEN B", "RÉGIMEN DE CAPITAL · PANTALLA B"),
    ("ON-CHAIN & MINERS ANALYSIS", "ANÁLISIS ON-CHAIN & MINERS"),
    ("MINER TREASURY · SCREEN B", "TESORERÍA DE MINEROS · PANTALLA B"),
    ("SELLING PRESSURE / ECONOMICS · SCREEN B", "PRESIÓN DE VENTA / ECONOMÍA · PANTALLA B"),
    ("NETWORK HEALTH · SCREEN B", "SALUD DE RED · PANTALLA B"),
    ("MINER REGIME · SCREEN B", "RÉGIMEN DE MINEROS · PANTALLA B"),
    ("VOLATILITY & MARKET REGIMES · SCREEN B", "VOLATILIDAD & REGÍMENES DE MERCADO · PANTALLA B"),
    ("VOLATILITY LEVEL · SCREEN B", "NIVEL DE VOLATILIDAD · PANTALLA B"),
    ("VOLATILITY PRICING · SCREEN B", "PRECIO DE VOLATILIDAD · PANTALLA B"),
    ("OPTIONS STRUCTURE · SCREEN B", "ESTRUCTURA DE OPCIONES · PANTALLA B"),
    ("VOLATILITY DYNAMICS · SCREEN B", "DINÁMICA DE VOLATILIDAD · PANTALLA B"),
    ("REGIME · SCREEN B", "RÉGIMEN · PANTALLA B"),
    ("VOLATILITY & REGIMES ANALYSIS ↗", "ANÁLISIS DE VOLATILIDAD Y REGÍMENES ↗"),
    ("LIQUIDITY MICROSTRUCTURE", "MICROESTRUCTURA DE LIQUIDEZ"),
    ("Order-book depth, whale behavior, executed liquidity & microstructure regimes", "Profundidad del libro, comportamiento de órdenes ballena, liquidez ejecutada y regímenes de microestructura"),
    ("CVD & ORDER FLOW", "CVD & ORDER FLOW"),
    ("Cumulative volume delta, trades & market microstructure", "Delta de volumen acumulado, operaciones y microestructura de mercado"),
    ("ETF & Exchange Flows", "ETF & Flujos de Exchanges"),
    ("ON-CHAIN & MINERS METRICS", "MÉTRICAS ON-CHAIN & MINEROS"),
    ("No indicators selected for analysis on Screen B.", "No seleccionaste indicadores de análisis en la Pantalla B."),
    ("No indicators selected for Screen B. Return to Screen A, select the desired indicators and open FUNDAMENTAL TECHNICAL ANALYSIS.", "No seleccionaste indicadores para la Pantalla B. Regresa a la Pantalla A, selecciona los indicadores deseados y abre ANÁLISIS TÉCNICO FUNDAMENTAL."),
    ("No metrics selected for Screen B. Return to Screen A, select Dynamics, Price × Participation, Crowding or Regime Shift and open the analysis.", "No seleccionaste métricas para la Pantalla B. Regresa a la Pantalla A, selecciona Dinámica, Price × Participación, Crowding o Regime Shift y abre el análisis."),
    ("No indicators selected for Screen B.", "No seleccionaste indicadores de Pantalla B."),
    ("No metrics selected for Screen B.", "No seleccionaste métricas de Pantalla B."),
    ("Screen B uses native order-flow analytics and does not overlay them on CVD candles.", "Pantalla B usa analítica nativa de order flow y no la superpone a las velas CVD."),
    ("Screen A keeps overlays on CVD.", "Pantalla A conserva overlays sobre CVD."),
    ("Independent charts on Screen B; they are not overlaid on Exchange Balance.", "Gráficas independientes en Pantalla B; no se superponen a Exchange Balance."),
    ("Native volatility analytics. The HMI only plots metrics precomputed by Processing; it does not apply RSI/MACD/ATR or moving averages to volatility.", "Analítica nativa de volatilidad. La HMI solo grafica métricas precomputadas por Processing; no aplica RSI/MACD/ATR ni medias móviles a volatilidad."),
    ("Screen B specialized in miner treasury, selling pressure, mining economics, network health and regime change. The HMI only plots results precomputed by Processing.", "Pantalla B especializada en tesorería de mineros, presión de venta, economía minera, salud de red y cambio de régimen. La HMI solo grafica resultados precalculados por Processing."),
    ("Native Screen B: realized liquidations, cascades, crowding and regime. Long/Short Ratio is positioning; it is not interpreted as a realized liquidation.", "Pantalla B nativa: liquidaciones realizadas, cascadas, crowding y régimen. Long/Short Ratio es posicionamiento; no se interpreta como liquidación realizada."),
    ("OPEN INTEREST OHLC UNAVAILABLE IN JSON", "OPEN INTEREST OHLC NO DISPONIBLE EN EL JSON"),
    ("No data", "Sin datos"),
    ("NO DATA", "SIN DATOS"),
    ("Price", "Precio"),
    ("Current Price", "Precio Actual"),
    ("Change 24H", "Cambio 24H"),
    ("High 24H", "Máx. 24H"),
    ("Low 24H", "Mín. 24H"),
    ("Volume 24H", "Volumen 24H"),
    ("Market Cap", "Capitalización"),
    ("MARKET CAP", "CAPITALIZACIÓN"),
    ("Volatility (ATR %)", "Volatilidad (ATR %)"),
    ("Average Range (24H)", "Rango Promedio (24H)"),
    ("AVERAGE RANGE (24H)", "RANGO PROMEDIO (24H)"),
    ("VOLATILITY (ATR %)", "VOLATILIDAD (ATR %)"),
    ("visible", "visibles"),
    ("PRICES / OHLCV", "PRECIOS / OHLCV"),
    ("Prices Ohlcv", "Prices · OHLCV"),
    ("Indicators", "Indicadores"),
    ("TREND", "TENDENCIA"),
    ("BANDS, LEVELS & CHANNELS · ON PRICE", "BANDAS, NIVELES Y CANALES · SOBRE PRECIO"),
    ("Support", "Soportes"),
    ("Resistance", "Resistencias"),
    ("Regression Channel", "Canal de Regresión"),
    ("Independent charts.", "Gráficas independientes."),
    ("Independent charts on Screen B; they are not overlaid on CVD candles.", "Gráficas independientes en Pantalla B; no se superponen a las velas CVD."),
    ("Screen A keeps overlays on CVD. Screen B uses native order-flow analytics precomputed by Processing (precomputed Processing contract).", "Pantalla A conserva overlays sobre CVD. Pantalla B usa analítica nativa de order flow precomputada por Processing (fixture demo en este contrato)."),
    ("Independent chart on Screen B; it is not overlaid on Exchange Balance.", "Gráfica independiente en Pantalla B; no se superpone a Exchange Balance."),
    ("Bid/ask depth asymmetry and normalized pressure", "Asimetría de profundidad bid/ask y presión normalizada"),
    ("Execution friction and deterioration of available liquidity", "Fricción de ejecución y deterioro de la liquidez disponible"),
    ("Resting walls and thin-book directional gaps", "Walls en reposo y gaps direccionales de libro delgado"),
    ("Persistence of large resting orders versus rapid withdrawal", "Persistencia de órdenes grandes en reposo frente a retiro rápido"),
    ("Aggressive flow absorbed by visible opposing liquidity", "Flujo agresivo absorbido por liquidez visible opuesta"),
    ("Composite microstructure state and regime displacement", "Estado compuesto de microestructura y desplazamiento de régimen"),
    ("They are not overlaid on or used to modify the candle reading.", "No se superponen ni modifican la lectura de las velas."),
    ("Delta 1H", "Delta 1H"),
    ("Buy/Sell", "Compra/Venta"),
    ("Buy Share", "Participación Compradora"),
    ("Futures Volume Usd", "Volumen Futures USD"),
    ("Futures vs Spot Volume Ratio", "Ratio de Volumen Futures vs Spot"),
    ("Flow Efficiency", "Eficiencia de Flujo"),
    ("Order Flow Imbalance", "Desequilibrio de Order Flow"),
    ("CVD SPOT", "CVD SPOT"),
    ("SPOT BUY / SELL DELTA", "DELTA COMPRA / VENTA SPOT"),
    ("CVD FUTURES / PERPETUALS", "CVD FUTURES / PERPETUALES"),
    ("FUTURES BUY / SELL DELTA", "DELTA COMPRA / VENTA FUTURES"),
    ("CVD Slope / Acceleration", "Pendiente / Aceleración CVD"),
    ("Buy/Sell Imbalance", "Desequilibrio Compra/Venta"),
    ("Price ↔ CVD Divergence", "Precio ↔ Divergencia CVD"),
    ("Spot ↔ Futures CVD Divergence", "Divergencia CVD Spot ↔ Futures"),
    ("Wasserstein Distance", "Distancia Wasserstein"),
    ("CVD SLOPE / ACCELERATION", "PENDIENTE / ACELERACIÓN CVD"),
    ("BUY / SELL IMBALANCE", "DESEQUILIBRIO COMPRA / VENTA"),
    ("PRICE ↔ CVD DIVERGENCE", "PRECIO ↔ DIVERGENCIA CVD"),
    ("SPOT ↔ FUTURES CVD DIVERGENCE", "DIVERGENCIA CVD SPOT ↔ FUTURES"),
    ("WASSERSTEIN DISTANCE", "DISTANCIA WASSERSTEIN"),
    ("OI ROC / SLOPE / ACCELERATION", "OI ROC / PENDIENTE / ACELERACIÓN"),
    ("OI Z-SCORE / PERCENTILE", "OI Z-SCORE / PERCENTIL"),
    ("PRICE × OPEN INTEREST REGIME", "PRECIO × RÉGIMEN OPEN INTEREST"),
    ("PRICE ↔ OPEN INTEREST DIVERGENCE", "PRECIO ↔ DIVERGENCIA OPEN INTEREST"),
    ("FUNDING × OPEN INTEREST CROWDING", "FUNDING × CROWDING OPEN INTEREST"),
    ("WASSERSTEIN / REGIME SHIFT", "WASSERSTEIN / CAMBIO DE RÉGIMEN"),
    ("OI ROC / SLOPE / ACCEL.", "OI ROC / PENDIENTE / ACEL."),
    ("PRICE × OI REGIME", "PRECIO × RÉGIMEN OI"),
    ("PRICE ↔ OI DIVERGENCE", "PRECIO ↔ DIVERGENCIA OI"),
    ("FUNDING × OI CROWDING", "FUNDING × CROWDING OI"),
    ("LEVERAGE / CROWDING", "APALANCAMIENTO / CROWDING"),
    ("ETF FLOW MOMENTUM / PERSISTENCE", "MOMENTUM / PERSISTENCIA DEL FLUJO ETF"),
    ("ETF FLOW Z-SCORE", "Z-SCORE DEL FLUJO ETF"),
    ("BTC PRICE ↔ ETF FLOW DIVERGENCE", "PRECIO BTC ↔ DIVERGENCIA DEL FLUJO ETF"),
    ("EXCHANGE FLOW PRESSURE", "PRESIÓN DE FLUJO EN EXCHANGES"),
    ("EXCHANGE RESERVE CHANGE / Z-SCORE", "CAMBIO DE RESERVA EN EXCHANGES / Z-SCORE"),
    ("ETF × EXCHANGE CAPITAL REGIME / WASSERSTEIN", "ETF × RÉGIMEN DE CAPITAL EN EXCHANGES / WASSERSTEIN"),
    ("MINER RESERVE CHANGE / Z-SCORE", "CAMBIO DE RESERVA DE MINEROS / Z-SCORE"),
    ("MPI / MINER-TO-EXCHANGE PRESSURE", "MPI / PRESIÓN MINER-TO-EXCHANGE"),
    ("PUELL MULTIPLE / REVENUE STRESS", "PUELL MULTIPLE / ESTRÉS DE INGRESOS"),
    ("HASHRATE MOMENTUM / HASH RIBBON", "MOMENTUM HASHRATE / HASH RIBBON"),
    ("HASHRATE × DIFFICULTY STRESS", "HASHRATE × ESTRÉS DE DIFFICULTY"),
    ("CAPITULATION / RECOVERY + WASSERSTEIN", "CAPITULACIÓN / RECUPERACIÓN + WASSERSTEIN"),
    ("MINER REGIME SUMMARY", "RESUMEN DEL RÉGIMEN MINERO"),
    ("VOLATILITY Z-SCORE / PERCENTILE", "VOLATILIDAD Z-SCORE / PERCENTIL"),
    ("VOLATILITY RISK PREMIUM", "PRIMA DE RIESGO DE VOLATILIDAD"),
    ("IV TERM STRUCTURE / SLOPE", "ESTRUCTURA TEMPORAL IV / PENDIENTE"),
    ("VOLATILITY SKEW / TAIL RISK", "SKEW DE VOLATILIDAD / RIESGO DE COLA"),
    ("VOL-OF-VOL / ACCELERATION", "VOL-OF-VOL / ACELERACIÓN"),
    ("REGIME SHIFT / WASSERSTEIN", "CAMBIO DE RÉGIMEN / WASSERSTEIN"),
    ("LIQUIDATION INTENSITY / Z-SCORE", "INTENSIDAD DE LIQUIDACIONES / Z-SCORE"),
    ("LONG VS SHORT LIQUIDATION IMBALANCE", "DESEQUILIBRIO DE LIQUIDACIONES LONG VS SHORT"),
    ("LIQUIDATION CASCADE / ACCELERATION", "CASCADA DE LIQUIDACIONES / ACELERACIÓN"),
    ("PRICE × LIQUIDATION REGIME", "PRECIO × RÉGIMEN DE LIQUIDACIONES"),
    ("LONG/SHORT CROWDING × LIQUIDATION PRESSURE", "CROWDING LONG/SHORT × PRESIÓN DE LIQUIDACIONES"),
    ("LIQUIDATION REGIME / HMI", "RÉGIMEN DE LIQUIDACIONES / HMI"),
    ("LIQUIDATION REGIME / HMI + WASSERSTEIN", "RÉGIMEN DE LIQUIDACIONES / HMI + WASSERSTEIN"),
    ("DEPTH IMBALANCE / PRESSURE", "DESEQUILIBRIO DE PROFUNDIDAD / PRESIÓN"),
    ("SPREAD × MARKET IMPACT / LIQUIDITY STRESS", "SPREAD × IMPACTO DE MERCADO / ESTRÉS DE LIQUIDEZ"),
    ("LIQUIDITY WALL / CONCENTRATION + VACUUM", "WALL DE LIQUIDEZ / CONCENTRACIÓN + VACUUM"),
    ("WHALE PERSISTENCE / CANCELLATION ACTIVITY", "PERSISTENCIA WHALE / ACTIVIDAD DE CANCELACIÓN"),
    ("EXECUTED LIQUIDITY / ABSORPTION", "LIQUIDEZ EJECUTADA / ABSORCIÓN"),
    ("LIQUIDITY REGIME / HMI + WASSERSTEIN", "RÉGIMEN DE LIQUIDEZ / HMI + WASSERSTEIN"),
    ("BOLLINGER BAND WIDTH (20,2)", "ANCHO DE BANDAS DE BOLLINGER (20,2)"),
    ("OI CHANGE 24H", "CAMBIO OI 24H"),
    ("OI FUNDING STATE", "ESTADO OI / FUNDING"),
    ("PROVIDER AVAILABILITY", "DISPONIBILIDAD DE PROVEEDORES"),
    ("FUNDING RATE", "TASA DE FUNDING"),
    ("EST. LEVERAGE RATIO", "RATIO DE APALANCAMIENTO EST."),
    ("BANDS & CHANNELS · ON OPEN INTEREST", "BANDAS Y CANALES · SOBRE OPEN INTEREST"),
    ("OI ROC / Slope / Acceleration", "OI ROC / Pendiente / Aceleración"),
    ("OI Z-Score / Percentile", "OI Z-Score / Percentil"),
    ("Price × OI Regime", "Precio × Régimen OI"),
    ("Price ↔ OI Divergence", "Precio ↔ Divergencia OI"),
    ("Funding × OI Crowding", "Funding × Crowding OI"),
    ("Wasserstein / Regime Shift", "Wasserstein / Cambio de Régimen"),
    ("ETF Net Flow", "Flujo Neto ETF"),
    ("Etf Net Flow", "Flujo Neto ETF"),
    ("Total Aum", "AUM Total"),
    ("Total AUM", "AUM Total"),
    ("CUMULATIVE ETF NET FLOW", "FLUJO NETO ETF ACUMULADO"),
    ("Exchange Inflow", "Entrada a Exchanges"),
    ("Exchange Outflow", "Salida de Exchanges"),
    ("Exchange Balance", "Balance de Exchanges"),
    ("Gbtc Premium", "Prima GBTC"),
    ("GBTC Premium", "Prima GBTC"),
    ("Exchange Flow Pressure", "Presión de Flujo en Exchanges"),
    ("Ticker", "Ticker"),
    ("Fund Name", "Nombre del Fondo"),
    ("Provider", "Proveedor"),
    ("Endpoint Id", "ID Endpoint"),
    ("Status", "Estado"),
    ("Reason", "Motivo"),
    ("Flow Usd", "Flujo USD"),
    ("Signed Flow Share", "Participación de Flujo con Signo"),
    ("ETF Flow Momentum / Persistence", "Momentum / Persistencia del Flujo ETF"),
    ("ETF Flow Z-Score", "Z-Score del Flujo ETF"),
    ("BTC Price ↔ ETF Flow Divergence", "Precio BTC ↔ Divergencia del Flujo ETF"),
    ("Exchange Reserve Change / Z-Score", "Cambio de Reserva en Exchanges / Z-Score"),
    ("ETF × Exchange Capital Regime / Wasserstein", "ETF × Régimen de Capital en Exchanges / Wasserstein"),
    ("MINER PRESSURE", "PRESIÓN DE MINEROS"),
    ("RESERVE TREND", "TENDENCIA DE RESERVAS"),
    ("NET POSITION", "POSICIÓN NETA"),
    ("SOPR REGIME", "RÉGIMEN SOPR"),
    ("MINER RESERVE (BTC)", "RESERVA DE MINEROS (BTC)"),
    ("SOPR / ASOPR CONTEXT", "CONTEXTO SOPR / ASOPR"),
    ("NETWORK HASHRATE", "HASHRATE DE RED"),
    ("MINING DIFFICULTY", "DIFICULTAD DE MINADO"),
    ("NATIVE METRICS", "MÉTRICAS NATIVAS"),
    ("Miner Reserve Change / Z-Score", "Cambio de Reserva de Mineros / Z-Score"),
    ("MPI / Miner-to-Exchange Pressure", "MPI / Presión Miner-to-Exchange"),
    ("Puell Multiple / Revenue Stress", "Puell Multiple / Estrés de Ingresos"),
    ("Hashrate Momentum / Hash Ribbon", "Momentum de Hashrate / Hash Ribbon"),
    ("Hashrate × Difficulty Stress", "Hashrate × Estrés de Dificultad"),
    ("Capitulation / Recovery + Wasserstein", "Capitulación / Recuperación + Wasserstein"),
    ("CURRENT REGIME", "RÉGIMEN ACTUAL"),
    ("REALIZED VOL 7D", "VOLATILIDAD REALIZADA 7D"),
    ("IMPLIED VOL / DVOL", "VOLATILIDAD IMPLÍCITA / DVOL"),
    ("VOL RISK PREMIUM", "PRIMA DE RIESGO DE VOLATILIDAD"),
    ("25Δ SKEW", "SKEW 25Δ"),
    ("REGIME CONFIDENCE", "CONFIANZA DEL RÉGIMEN"),
    ("REALIZED VOLATILITY · RV7D / RV30D", "VOLATILIDAD REALIZADA · RV7D / RV30D"),
    ("IMPLIED VOLATILITY · DVOL / IV1M", "VOLATILIDAD IMPLÍCITA · DVOL / IV1M"),
    ("IMPLIED VS REALIZED · VRP", "IMPLÍCITA VS REALIZADA · VRP"),
    ("IV TERM STRUCTURE", "ESTRUCTURA TEMPORAL IV"),
    ("Volatility Z-Score / Percentile", "Volatilidad Z-Score / Percentil"),
    ("Volatility Risk Premium", "Prima de Riesgo de Volatilidad"),
    ("IV Term Structure / Slope", "Estructura Temporal IV / Pendiente"),
    ("Volatility Skew / Tail Risk", "Skew de Volatilidad / Riesgo de Cola"),
    ("Vol-of-Vol / Acceleration", "Vol-of-Vol / Aceleración"),
    ("Regime Shift / Wasserstein", "Cambio de Régimen / Wasserstein"),
    ("LONG / SHORT LIQUIDATIONS", "LIQUIDACIONES LONG / SHORT"),
    ("BITCOIN EXCHANGE LIQUIDATION MAP", "MAPA DE LIQUIDACIONES DE EXCHANGES BTC"),
    ("LONG / SHORT POSITIONING", "POSICIONAMIENTO LONG / SHORT"),
    ("LIQUIDITY TARGET SUMMARY", "RESUMEN DE OBJETIVOS DE LIQUIDEZ"),
    ("Liquidation Regime", "Régimen de Liquidaciones"),
    ("Pressure Score", "Puntaje de Presión"),
    ("Pressure Label", "Etiqueta de Presión"),
    ("Dominant Side", "Lado Dominante"),
    ("Side Imbalance", "Desequilibrio por Lado"),
    ("Top Exchange Conc.", "Concentración Principal de Exchange"),
    ("Max Event Spike", "Pico Máx. de Evento"),
    ("Max Single Liq.", "Liquidación Individual Máx."),
    ("Nearest Long Cluster", "Cluster Long Más Cercano"),
    ("Nearest Short Cluster", "Cluster Short Más Cercano"),
    ("HYPERLIQUID LIQUIDATION MAP", "MAPA DE LIQUIDACIONES HYPERLIQUID"),
    ("BINANCE BTC/USDT LIQUIDATION MAP", "MAPA DE LIQUIDACIONES BINANCE BTC/USDT"),
    ("Bid Depth", "Profundidad Bid"),
    ("Ask Depth", "Profundidad Ask"),
    ("Liquidity Imbalance", "Desequilibrio de Liquidez"),
    ("Mid Price", "Precio Medio"),
    ("Impact 1 BTC", "Impacto 1 BTC"),
    ("1. ORDER BOOK", "1. LIBRO DE ÓRDENES"),
    ("2. WHALE ORDERS", "2. ÓRDENES BALLENA"),
    ("3. LARGE TRADES", "3. OPERACIONES GRANDES"),
    ("4. EXECUTED LIQUIDITY / OPERATIONS", "4. LIQUIDEZ EJECUTADA / OPERACIONES"),
    ("ORDER DEPTH", "PROFUNDIDAD DEL LIBRO"),
    ("WHALE LIQUIDITY PROFILE", "PERFIL DE LIQUIDEZ BALLENA"),
    ("EXECUTED LIQUIDITY PROFILE", "PERFIL DE LIQUIDEZ EJECUTADA"),
    ("ORDER BOOK SNAPSHOT", "SNAPSHOT DEL LIBRO DE ÓRDENES"),
    ("BIDS", "BIDS / COMPRAS"),
    ("ASKS", "ASKS / VENTAS"),
    ("Price (USDT)", "Precio (USDT)"),
    ("Size (BTC)", "Tamaño (BTC)"),
    ("Cumulative (BTC)", "Acumulado (BTC)"),
    ("DEPTH IMBALANCE / PRESSURE", "DESEQUILIBRIO DE PROFUNDIDAD / PRESIÓN"),
    ("SPREAD × MARKET IMPACT / LIQUIDITY STRESS", "SPREAD × IMPACTO DE MERCADO / ESTRÉS DE LIQUIDEZ"),
    ("LIQUIDITY WALL / CONCENTRATION + VACUUM", "MURO DE LIQUIDEZ / CONCENTRACIÓN + VACÍO"),
    ("WHALE PERSISTENCE / CANCELLATION ACTIVITY", "PERSISTENCIA BALLENA / ACTIVIDAD DE CANCELACIÓN"),
    ("EXECUTED LIQUIDITY / ABSORPTION", "LIQUIDEZ EJECUTADA / ABSORCIÓN"),
    ("LIQUIDITY REGIME / HMI + WASSERSTEIN", "RÉGIMEN DE LIQUIDEZ / HMI + WASSERSTEIN"),
    ("Demo", "Demo"),
    ("Synthetic", "Sintético"),
    ("Estimated", "Estimado"),
    ("Partial", "Parcial"),
    ("DEMO READY", "DEMO LISTO"),
    ("SYNTHETIC_CALIBRATED", "SINTÉTICO_CALIBRADO"),
    ("CONTRACTING", "CONTRACCIÓN"),
    ("EXPANDING / POSITIVE", "EXPANSIÓN / POSITIVO"),
    ("POSITIVE FUNDING EXPANSION", "EXPANSIÓN CON FUNDING POSITIVO"),
    ("FUTURES_DOMINANT", "FUTURES_DOMINANTE"),
    ("LOW", "BAJO"),
    ("LOW_SELLING_PRESSURE", "BAJA_PRESIÓN_DE_VENTA"),
    ("INCREASING", "CRECIENTE"),
    ("NET_ACCUMULATION", "ACUMULACIÓN_NETA"),
    ("PROFIT", "GANANCIA"),
    ("UNKNOWN", "DESCONOCIDO"),
    ("CALM", "CALMO"),
    ("HIGH", "ALTO"),
    ("VOLATILITY REGIME SUMMARY", "RESUMEN DEL RÉGIMEN DE VOLATILIDAD"),
    ("LIQUIDATIONS ANALYSIS ↗", "ANÁLISIS DE LIQUIDACIONES ↗"),
    ("LIQUIDATIONS & POSITIONING · SCREEN B", "LIQUIDACIONES Y POSICIONAMIENTO · PANTALLA B"),
    ("Select native analysis panels.", "Selecciona paneles de análisis nativos."),
    ("Native Screen B: realized liquidations, cascades, crowding and regime. Long/Short Ratio is positioning; it is not interpreted as a realized liquidation.", "Pantalla B nativa: liquidaciones realizadas, cascadas, crowding y régimen. Long/Short Ratio es posicionamiento; no se interpreta como liquidación realizada."),
)

EN_TO_ES = {en: es for en, es in _PAIRS}
ES_TO_EN = {es: en for en, es in _PAIRS}

SOURCE_ALIASES_EN = {
    "prices": "Prices",
    "Prices Ohlcv": "Prices · OHLCV",
    "open_interest_and_funding": "Open Interest & Funding",
    "Open Interest And Funding": "Open Interest & Funding",
    "Etf Exchange Flows": "ETF & Exchange Flows",
    "On Chain Miners": "On-Chain Miners",
    "volatility_market_regimes": "Volatility & Market Regimes",
    "Volatility Market Regimes": "Volatility & Market Regimes",
    "Long Short Liquidations": "Long / Short Liquidations",
    "Alta": "High",
    "(Selecciona para mostrar)": "(Select to display)",
    "ANÁLISIS DE FLUJOS Y CAPITAL": "FLOW & CAPITAL ANALYSIS",
    "ANÁLISIS": "ANALYSIS",
    "Pantalla A conserva overlays sobre CVD. Pantalla B usa analítica nativa de order flow precomputada por Processing (fixture demo en este contrato).": "Screen A keeps overlays on CVD. Screen B uses native order-flow analytics precomputed by Processing (precomputed Processing contract).",
    "Gráficas independientes en Pantalla B; no se superponen a las velas CVD.": "Independent charts on Screen B; they are not overlaid on CVD candles.",
    "Gráfica independiente en Pantalla B; no se superpone a Exchange Balance.": "Independent chart on Screen B; it is not overlaid on Exchange Balance.",
    "INSTITUTIONAL FLOW · PANTALLA B": "INSTITUTIONAL FLOW · SCREEN B",
    "PRICE & EXCHANGE CAPITAL · PANTALLA B": "PRICE & EXCHANGE CAPITAL · SCREEN B",
    "CAPITAL REGIME · PANTALLA B": "CAPITAL REGIME · SCREEN B",
    "Pantalla B especializada en treasury de mineros, presión de venta, economía minera, salud de red y cambio de régimen. La HMI solo grafica resultados precalculados por Processing.": "Screen B specialized in miner treasury, selling pressure, mining economics, network health and regime change. The HMI only plots results precomputed by Processing.",
    "MINER TREASURY · PANTALLA B": "MINER TREASURY · SCREEN B",
    "SELLING PRESSURE / ECONOMICS · PANTALLA B": "SELLING PRESSURE / ECONOMICS · SCREEN B",
    "NETWORK HEALTH · PANTALLA B": "NETWORK HEALTH · SCREEN B",
    "MINER REGIME · PANTALLA B": "MINER REGIME · SCREEN B",
    "VOLATILITY & MARKET REGIMES · PANTALLA B": "VOLATILITY & MARKET REGIMES · SCREEN B",
    "VOLATILITY LEVEL · PANTALLA B": "VOLATILITY LEVEL · SCREEN B",
    "VOLATILITY PRICING · PANTALLA B": "VOLATILITY PRICING · SCREEN B",
    "OPTIONS STRUCTURE · PANTALLA B": "OPTIONS STRUCTURE · SCREEN B",
    "VOLATILITY DYNAMICS · PANTALLA B": "VOLATILITY DYNAMICS · SCREEN B",
    "REGIME · PANTALLA B": "REGIME · SCREEN B",
    "Profundidad acumulada del libro": "Accumulated order-book depth",
    "Órdenes de tamaño extraordinario y liquidez asociada": "Large resting orders and associated liquidity",
    "Operaciones grandes ejecutadas y liquidez consumida": "Large executed trades and consumed liquidity",
}

SOURCE_ALIASES_ES = {
    "prices": "Precios",
    "Prices Ohlcv": "Precios · OHLCV",
    "open_interest_and_funding": "Open Interest & Funding",
    "Open Interest And Funding": "Open Interest & Funding",
    "Etf Exchange Flows": "ETF & Flujos de Exchanges",
    "On Chain Miners": "On-Chain & Mineros",
    "volatility_market_regimes": "Volatilidad & Regímenes de Mercado",
    "Volatility Market Regimes": "Volatilidad & Regímenes de Mercado",
    "Long Short Liquidations": "Liquidaciones Long / Short",
    "Alta": "Alta",
    "(Selecciona para mostrar)": "(Selecciona para mostrar)",
    "ANÁLISIS DE FLUJOS Y CAPITAL": "ANÁLISIS DE FLUJOS Y CAPITAL",
    "ANÁLISIS": "ANÁLISIS",
    "Pantalla A conserva overlays sobre CVD. Pantalla B usa analítica nativa de order flow precomputada por Processing (fixture demo en este contrato).": "Pantalla A conserva overlays sobre CVD. Pantalla B usa analítica nativa de order flow precomputada por Processing (fixture demo en este contrato).",
    "Gráficas independientes en Pantalla B; no se superponen a las velas CVD.": "Gráficas independientes en Pantalla B; no se superponen a las velas CVD.",
    "Gráfica independiente en Pantalla B; no se superpone a Exchange Balance.": "Gráfica independiente en Pantalla B; no se superpone a Exchange Balance.",
    "INSTITUTIONAL FLOW · PANTALLA B": "FLUJO INSTITUCIONAL · PANTALLA B",
    "PRICE & EXCHANGE CAPITAL · PANTALLA B": "PRICE & CAPITAL EN EXCHANGES · PANTALLA B",
    "CAPITAL REGIME · PANTALLA B": "RÉGIMEN DE CAPITAL · PANTALLA B",
    "Pantalla B especializada en treasury de mineros, presión de venta, economía minera, salud de red y cambio de régimen. La HMI solo grafica resultados precalculados por Processing.": "Pantalla B especializada en tesorería de mineros, presión de venta, economía minera, salud de red y cambio de régimen. La HMI solo grafica resultados precalculados por Processing.",
    "MINER TREASURY · PANTALLA B": "TESORERÍA DE MINEROS · PANTALLA B",
    "SELLING PRESSURE / ECONOMICS · PANTALLA B": "PRESIÓN DE VENTA / ECONOMÍA · PANTALLA B",
    "NETWORK HEALTH · PANTALLA B": "SALUD DE RED · PANTALLA B",
    "MINER REGIME · PANTALLA B": "RÉGIMEN DE MINEROS · PANTALLA B",
    "VOLATILITY & MARKET REGIMES · PANTALLA B": "VOLATILIDAD & REGÍMENES DE MERCADO · PANTALLA B",
    "VOLATILITY LEVEL · PANTALLA B": "NIVEL DE VOLATILIDAD · PANTALLA B",
    "VOLATILITY PRICING · PANTALLA B": "PRECIO DE VOLATILIDAD · PANTALLA B",
    "OPTIONS STRUCTURE · PANTALLA B": "ESTRUCTURA DE OPCIONES · PANTALLA B",
    "VOLATILITY DYNAMICS · PANTALLA B": "DINÁMICA DE VOLATILIDAD · PANTALLA B",
    "REGIME · PANTALLA B": "RÉGIMEN · PANTALLA B",
    "Profundidad acumulada del libro": "Profundidad acumulada del libro",
    "Órdenes de tamaño extraordinario y liquidez asociada": "Órdenes grandes en reposo y liquidez asociada",
    "Operaciones grandes ejecutadas y liquidez consumida": "Operaciones grandes ejecutadas y liquidez consumida",
}


def normalize_locale(value: Any) -> str:
    locale = str(value or "").strip().lower()
    return locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE


def locale_from_search(search: str | None) -> str:
    """Resolve locale from the URL query string.

    The URL is the only persistent/source-of-truth state for language:
    ``?lang=en`` or ``?lang=es``. Missing/invalid values resolve to English.
    """
    raw = str(search or "").lstrip("?")
    values = parse_qs(raw, keep_blank_values=True).get("lang", [])
    return normalize_locale(values[0] if values else DEFAULT_LOCALE)


_ACTIVE_LOCALE: ContextVar[str] = ContextVar("tradelatin_locale", default=DEFAULT_LOCALE)


@contextmanager
def locale_context(locale: str | None):
    """Bind one explicit locale while a Dash callback builds components.

    This context is request/callback-local and never stored in cookies,
    localStorage or global mutable state. It exists only so existing helpers
    can call ``current_locale()`` without threading a locale argument through
    every HMI helper function.
    """
    token = _ACTIVE_LOCALE.set(normalize_locale(locale))
    try:
        yield
    finally:
        _ACTIVE_LOCALE.reset(token)


def current_locale() -> str:
    """Return the locale explicitly bound for the current render callback."""
    return normalize_locale(_ACTIVE_LOCALE.get())


def localized_href(path: str, locale: str | None = None) -> str:
    """Return an internal HMI URL that preserves the explicit language state."""
    lang = normalize_locale(locale or current_locale())
    base = str(path or "/")
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}lang={lang}"


def _translate_exact(text: str, lang: str) -> str:
    if lang == "es":
        if text in SOURCE_ALIASES_ES:
            return SOURCE_ALIASES_ES[text]
        if text in EN_TO_ES:
            return EN_TO_ES[text]
        if text in ES_TO_EN:
            return text
    else:
        if text in SOURCE_ALIASES_EN:
            return SOURCE_ALIASES_EN[text]
        if text in ES_TO_EN:
            return ES_TO_EN[text]
        if text in EN_TO_ES:
            return text
    return text


_DYNAMIC_PREFIX_PAIRS: tuple[tuple[str, str], ...] = (
    ("Buy Share ", "Participación compradora "),
    ("Sell Share ", "Participación vendedora "),
    ("Futures Volume Usd ", "Volumen Futures USD "),
    ("Spot Volume Usd ", "Volumen Spot USD "),
    ("Capitulation ", "Capitulación "),
    ("VOLUME: ", "VOLUMEN: "),
    ("HISTOGRAM: ", "HISTOGRAMA: "),
    ("BUY: ", "COMPRA: "),
    ("SELL: ", "VENTA: "),
    ("NET: ", "NETO: "),
    ("Reserve: ", "Reserva: "),
)


def translate_text(value: Any, locale: str | None = None) -> Any:
    """Translate one visible UI string.

    Source strings are canonical English. The helper also tolerates legacy
    Spanish fixture text during migration, preserves whitespace, and handles
    numbered analysis labels and a very small set of dynamic metric prefixes.
    It never touches component IDs or financial contract keys.
    """
    if not isinstance(value, str):
        return value
    lang = normalize_locale(locale or current_locale())

    # Preserve intentional spaces in components such as ``"INDICATORS "``.
    core = value.strip()
    if not core:
        return value
    left = value[: len(value) - len(value.lstrip())]
    right = value[len(value.rstrip()) :]

    translated = _translate_exact(core, lang)
    if translated != core:
        return f"{left}{translated}{right}"

    # Analysis-card titles are frequently prefixed with ``1.`` ... ``6.``.
    numbered = re.match(r"^(\d+\.\s+)(.+)$", core)
    if numbered:
        suffix = _translate_exact(numbered.group(2), lang)
        if suffix != numbered.group(2):
            return f"{left}{numbered.group(1)}{suffix}{right}"

    # A few fixture display values contain a numeric suffix. Translate only
    # the descriptive prefix and leave the numeric payload untouched.
    for en_prefix, es_prefix in _DYNAMIC_PREFIX_PAIRS:
        source_prefix, target_prefix = (en_prefix, es_prefix) if lang == "es" else (es_prefix, en_prefix)
        if core.startswith(source_prefix):
            return f"{left}{target_prefix}{core[len(source_prefix):]}{right}"

    return value


def tr(value: Any, locale: str | None = None) -> Any:
    return translate_text(value, locale)


def locale_label(en: str, es: str, locale: str | None = None) -> str:
    return es if normalize_locale(locale or current_locale()) == "es" else en


def _localize_mapping(value: Any, locale: str) -> Any:
    if isinstance(value, str):
        return translate_text(value, locale)
    if isinstance(value, list):
        return [_localize_mapping(item, locale) for item in value]
    if isinstance(value, tuple):
        return tuple(_localize_mapping(item, locale) for item in value)
    if isinstance(value, dict):
        localized: dict[Any, Any] = {}
        for key, nested in value.items():
            if key in {"label", "title", "name", "text", "placeholder"}:
                localized[key] = _localize_mapping(nested, locale)
            else:
                localized[key] = nested
        return localized
    return value


def localize_options(options: Any, locale: str | None = None) -> Any:
    return _localize_mapping(options, normalize_locale(locale or current_locale()))


def localize_figure(figure: Any, locale: str | None = None) -> Any:
    lang = normalize_locale(locale or current_locale())
    if figure is None or not hasattr(figure, "layout") or not hasattr(figure, "data"):
        return figure
    try:
        title = getattr(getattr(figure.layout, "title", None), "text", None)
        if isinstance(title, str):
            figure.layout.title.text = translate_text(title, lang)
        for axis_name in ("xaxis", "yaxis", "xaxis2", "yaxis2", "xaxis3", "yaxis3"):
            axis = getattr(figure.layout, axis_name, None)
            axis_title = getattr(getattr(axis, "title", None), "text", None) if axis is not None else None
            if isinstance(axis_title, str):
                axis.title.text = translate_text(axis_title, lang)
        annotations = getattr(figure.layout, "annotations", None) or []
        for annotation in annotations:
            text = getattr(annotation, "text", None)
            if isinstance(text, str):
                annotation.text = translate_text(text, lang)
        for trace in figure.data:
            name = getattr(trace, "name", None)
            if isinstance(name, str):
                trace.name = translate_text(name, lang)
            hovertemplate = getattr(trace, "hovertemplate", None)
            if isinstance(hovertemplate, str):
                trace.hovertemplate = translate_text(hovertemplate, lang)
    except Exception:
        return figure
    return figure


def localize_component_tree(node: Any, locale: str | None = None) -> Any:
    """Translate visible Dash component props without touching IDs or contract data."""
    lang = normalize_locale(locale or current_locale())
    if node is None:
        return None
    if isinstance(node, str):
        return translate_text(node, lang)
    if isinstance(node, list):
        return [localize_component_tree(item, lang) for item in node]
    if isinstance(node, tuple):
        return tuple(localize_component_tree(item, lang) for item in node)
    if hasattr(node, "layout") and hasattr(node, "data"):
        return localize_figure(node, lang)
    if hasattr(node, "_prop_names"):
        for prop in getattr(node, "_prop_names", []):
            if not hasattr(node, prop):
                continue
            value = getattr(node, prop)
            if prop == "children":
                setattr(node, prop, localize_component_tree(value, lang))
            elif prop in {"title", "placeholder"} and isinstance(value, str):
                setattr(node, prop, translate_text(value, lang))
            elif prop == "options" and isinstance(value, list):
                setattr(node, prop, _localize_mapping(value, lang))
            elif prop == "columns" and isinstance(value, list):
                setattr(node, prop, _localize_mapping(value, lang))
            elif prop == "figure":
                setattr(node, prop, localize_figure(value, lang))
        return node
    return node
