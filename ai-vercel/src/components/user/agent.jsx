import React, { useState, useRef, useEffect, useCallback } from 'react'
import headerImg from '../../assets/header.png'
import agentImg from '../../assets/agent.png'
import Navbar from './navbar'
import Footer from './footer'
import api from '../../services/api'

/**
 * Agent chat UI implemented with Tailwind CSS.
 * Uses local assets: headerImg (as decorative mesh) and agentImg (assistant illustration).
 */

export default function Agent() {
	const [text, setText] = useState('')
	const [loading, setLoading] = useState(false)
	const [response, setResponse] = useState(null)
	const [expanded, setExpanded] = useState([])
	const [error, setError] = useState(null)
    const responseRef = useRef(null)
    const [latency, setLatency] = useState(null) // ms client-side


	const handleSend = useCallback(async () => {
			if (!text || text.trim() === '') return
			setLoading(true)
			setError(null)
			setLatency(null)
			const payload = text.trim()
			const start = Date.now()
			try {
				const res = await api.ai.process(payload)
				const took = Date.now() - start
				setLatency(took)
				const data = res?.data || {}
				// backend may include processing time in ms as `_processing_time_ms`
				if (data && data._processing_time_ms) {
					// prefer server-side processing time if provided
					data.server_processing_ms = data._processing_time_ms
				}
				setResponse(data)
			} catch (err) {
				console.error('AI request failed', err)
				if (!err.response) {
					// likely network error or timeout
					setError('Network/Timeout — pastikan backend AI berjalan (http://localhost:5000) atau periksa timeout pada client/server')
				} else {
					const msg = err.response?.data?.error || err.response?.data?.message || err.message || 'Terjadi kesalahan pada server'
					setError(msg)
				}
			} finally {
				setLoading(false)
				setText('')
			}
		}, [text])

	// Light mode only - no theme toggle
	const containerStyle = {
		backgroundColor: 'white',
		color: '#1e293b'
	}

	useEffect(() => {
		if (responseRef.current) {
			responseRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
		}
	}, [response])

	function toggleExpand(idx) {
		setExpanded((prev) => {
			if (prev.includes(idx)) return prev.filter((i) => i !== idx)
			return [...prev, idx]
		})
	}

	const headingClass = 'relative z-10 mt-8 text-2xl md:text-3xl font-poppins text-slate-800'
	const subtextClass = 'relative z-10 mt-8 text-left text-base font-semibold text-slate-600 max-w-3xl mx-auto'
	const chipClass = 'px-4 py-2 backdrop-blur-sm rounded-lg text-sm bg-white/70 text-[#090D3F] border border-white'
	const inputWrapperClass = 'relative flex items-center bg-white border-[rgba(22,2,17,0.12)] rounded-lg shadow-sm p-3'
	const inputClass = 'flex-1 px-4 py-3 pr-16 sm:pr-20 text-lg md:text-base placeholder:text-[#56637E] focus:outline-none text-slate-800 bg-transparent'
	const sendBtnClass = 'absolute right-2 top-1/2 -translate-y-1/2 w-14 h-12 sm:w-16 sm:h-12 rounded-full flex items-center justify-center shadow-lg ring-1 active:scale-95 transition bg-[#5465FF] ring-[#5465FF]/30 text-white'

	return (
		<div
			className="relative min-h-screen overflow-x-hidden bg-white text-slate-800 transition-colors font-poppins"
			style={containerStyle}
		>
			<Navbar />

			{/* decorative header/mesh background */}
			<div
				aria-hidden
				className="absolute inset-x-0 top-0 h-96 bg-no-repeat bg-center bg-cover -z-10"
				style={{ backgroundImage: `url(${headerImg})` }}
			/>

			<div className="relative mx-auto max-w-7xl px-6 lg:px-10 pt-28 pb-24">
				{/* Centered content area */}
				<div className="max-w-4xl mx-auto text-center relative">
					{/* soft colored blurred ellipses to mimic mesh gradient */}
					{/* soft gradient ellipse: pink / light purple -> light blue (matches screenshot) */}
					<div className="pointer-events-none absolute left-1/2 -translate-x-1/2 top-28 w-72 h-[330px] rounded-full bg-gradient-to-br from-[#FF86E1]/80 via-[#D9B3FF]/60 to-[#89BCFF]/80 blur-3xl opacity-90" />
					{/* agent illustration */}
					<div className="relative z-10 flex justify-center">
						<img src={agentImg} alt="AI Agent" className="w-48 h-48 object-contain" />
					</div>

					{/* headline */}
					<h2 className={headingClass}>
						Butuh bantuan rencanain wedding impianmu?
					</h2>

					{/* Suggestions title */}
					<p className={subtextClass}>
						Suggestions on what to ask Our AI
					</p>

					{/* suggestion chips */}
					<div className="relative z-10 mt-4 flex flex-wrap justify-start gap-4 max-w-3xl mx-auto">
						<button className={chipClass}>
							Mau hitung budget atau cari vendor? Ketik aja di sini
						</button>
						<button className={chipClass}>
							Dekorasi sesuai budget 20jt?
						</button>
						<button className={chipClass}>
							Vendor terbaik untuk outdoor wedding 🌿
						</button>
					</div>

					{/* main chat input container */}
					<div className="relative z-10 mt-8">
						<div className="mx-auto max-w-5xl">
							<div className={inputWrapperClass}>
								<input
									aria-label="Ask our AI"
									className={inputClass}
									placeholder="Tulis pertanyaan"
									value={text}
									onChange={(e) => setText(e.target.value)}
								/>
								<button
									onClick={handleSend}
									disabled={loading}
									aria-label="Send message"
									className={sendBtnClass}
								>
									{loading ? (
									<svg className="animate-spin w-6 h-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
										<circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
										<path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
									</svg>
									) : (
									<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7 sm:w-7 sm:h-7 text-white">
										<path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
									</svg>
									)}
								</button>
							</div>
						</div>
					</div>

					{/* Inline error near input */}
					{error && (
						<div className="max-w-5xl mx-auto mt-3 text-left">
							<div className="text-sm text-red-600 font-semibold">{error}</div>
						</div>
					)}
				</div>
			</div>

					{/* Response / results area */}
					{error && (
						<div className="mt-4 text-red-600 font-semibold">{error}</div>
					)}
					{response && (
						<div ref={responseRef} className="mt-6 text-left bg-white p-6 shadow-sm max-w-4xl mx-auto">
							{/* Timing diagnostics */}
							{(latency || response?.server_processing_ms) && (
								<div className="mb-3 text-sm text-slate-600">
									{latency ? <span>Client latency: <strong>{latency} ms</strong></span> : null}
									{(latency && response?.server_processing_ms) ? <span className="mx-2">•</span> : null}
									{response?.server_processing_ms ? <span>Server processing: <strong>{response.server_processing_ms} ms</strong></span> : null}
								</div>
							)}
						{response.generated_text && (
							<div className="mb-4 text-gray-800">
								<p className="text-base">{response.generated_text}</p>
							</div>
						)}
							{(!response.recommendations || response.recommendations.length === 0) ? (
								<div className="mb-4 p-4 bg-yellow-50 border-l-4 border-yellow-400 text-yellow-800">
									Maaf, tidak ada rekomendasi yang sesuai dengan kriteria Anda.
								</div>
							) : (
								<div className="mb-4">
									<strong>Rekomendasi</strong>
									<ul className="mt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
										{response.recommendations.map((r, idx) => {
											// prefer explicit columns requested by user
											const tema = r.tema || r.theme || '';
											const lokasi = r.lokasi || r.location || '';
											const budgetMin = r.budget_min || r.budgetMin || r.budget_minimum || r.budget_minimum || '';
											const budgetMax = r.budget_max || r.budgetMax || r.budget_maximum || r.budget_maximum || '';
											const jumlahTamu = r.jumlah_tamu || r.guests || r.jumlah || '';
											const tipeAcara = r.tipe_acara || r.event_type || '';
											const venue = r.venue || r.lokasi_venue || '';
											const waktu = r.waktu || r.time || r.date || '';
											return (
												<li key={idx} className="bg-white rounded-lg border border-gray-200 hover:shadow-sm transition h-full flex flex-col">
													<div className="flex-1 p-4 flex gap-4">
														<div className="w-20 h-20 bg-gradient-to-br from-[#EEF2FF] to-[#F6F8FF] rounded-md flex items-center justify-center text-indigo-600 font-semibold text-sm flex-shrink-0">Img</div>
														<div className="flex-1">
															{/* title (click to toggle detail) */}
															<div onClick={() => toggleExpand(idx)} role="button" tabIndex={0} onKeyDown={(e)=>{ if(e.key==='Enter') toggleExpand(idx)}} className="font-semibold text-gray-800 whitespace-normal mb-2 cursor-pointer">{r.name || r.nama}</div>
															{/* show only requested fields */}
															<div className="text-sm text-gray-600 space-y-1">
																{tema ? <div><span className="font-medium text-gray-700">Tema:</span> <span className="ml-1">{tema}</span></div> : null}
																{lokasi ? <div><span className="font-medium text-gray-700">Lokasi:</span> <span className="ml-1">{lokasi}</span></div> : null}
																{(budgetMin || budgetMax) ? <div><span className="font-medium text-gray-700">Budget:</span> <span className="ml-1">{budgetMin && budgetMax ? `Rp ${Number(budgetMin).toLocaleString()} - Rp ${Number(budgetMax).toLocaleString()}` : (budgetMin ? `Rp ${Number(budgetMin).toLocaleString()}` : `Rp ${Number(budgetMax).toLocaleString()}`)}</span></div> : null}
																{jumlahTamu ? <div><span className="font-medium text-gray-700">Jumlah tamu:</span> <span className="ml-1">{jumlahTamu}</span></div> : null}
																{tipeAcara ? <div><span className="font-medium text-gray-700">Tipe acara:</span> <span className="ml-1">{tipeAcara}</span></div> : null}
																{venue ? <div><span className="font-medium text-gray-700">Venue:</span> <span className="ml-1">{venue}</span></div> : null}
																{waktu ? <div><span className="font-medium text-gray-700">Waktu:</span> <span className="ml-1">{waktu}</span></div> : null}
															</div>
														</div>
													</div>
													<div className="p-4 pt-0 flex items-end justify-end gap-4">
														<button onClick={() => window.open('https://www.instagram.com/sepasang.wp', '_blank', 'noopener')} aria-label="Open sepasang.wp Instagram" className="mt-0 inline-flex items-center gap-2 px-3 py-1 rounded bg-[#5465FF] text-white text-sm">
															Vendor Information
														</button>
													</div>
												</li>
											)
										})}
									</ul>
								</div>
							)}
							{/* Visualization intentionally hidden for end users */}
						</div>
					)}
			<Footer />
		</div>
	)
}
