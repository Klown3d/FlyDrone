"""Replay one recorded heading trial and its actual saved PFL3 model activity."""
from pathlib import Path
import json
import numpy as np


def generate(root: Path) -> Path:
    directory=root/'results/neural/orientation_closed_loop'
    data=[]
    for scenario in ('ideal','noise_and_delay'):
        with np.load(directory/f'{scenario}-corrected-trace.npz') as trace:
            index=54  # Fixed goal +15 degrees, initial error +135 degrees; not optimized.
            data.append({'scenario':scenario,'goal':float(trace['goals_rad'][index]),
                'time':trace['time_s'].tolist(),'heading':trace['heading_rad'][:,index].tolist(),
                'error':trace['error_deg'][:,index].round(3).tolist(),
                'rates':trace['pfl3_rates_hz'][:,index,:].round(3).tolist()})
    document='''<!doctype html><html lang="es"><meta charset="utf-8"><title>FlyDrone · primera prueba de orientación</title>
<style>body{background:#0d1728;color:#eef4ff;font:16px system-ui;margin:28px auto;max-width:950px;padding:0 20px}p{color:#b9c6dc;line-height:1.5}canvas{background:#14233b;width:100%;height:420px;border-radius:12px}button,select{padding:10px;background:#263b5a;color:white;border:1px solid #6682a6;border-radius:6px}input{width:100%}#stats{padding:14px}</style>
<h1>Primera prueba dinámica de orientación</h1><p>Reproducción de un ensayo guardado: meta +15°, error inicial +135°. Modelo provisional FlyWire 783. Es una simulación de orientación, todavía no un vuelo de dron.</p>
<select id="scenario"><option value="0">Entradas ideales</option><option value="1">Ruido 3° y retraso 150 ms</option></select> <button id="play">Reproducir / pausar</button><div id="stats"></div><canvas id="canvas"></canvas><input id="time" type="range" min="0" max="400" value="0" aria-label="Tiempo del ensayo"><p>Flecha turquesa: orientación actual. Flecha amarilla: meta. Barras: tasas PFL3 calculadas y guardadas para las 24 neuronas. No son mediciones de actividad de una mosca real.</p>
<script>const data=__DATA__,c=document.querySelector('#canvas'),ctx=c.getContext('2d'),slider=document.querySelector('#time'),scenario=document.querySelector('#scenario');let playing=false,last=0;
function draw(){c.width=900;c.height=420;ctx.clearRect(0,0,900,420);const d=data[Number(scenario.value)],i=Number(slider.value);document.querySelector('#stats').textContent=`Tiempo ${d.time[i].toFixed(2)} s · error ${d.error[i].toFixed(2)}°`;ctx.strokeStyle='#8294b0';ctx.beginPath();ctx.arc(210,200,120,0,2*Math.PI);ctx.stroke();function arrow(a,color,length){ctx.strokeStyle=color;ctx.lineWidth=5;const x=210+length*Math.cos(a),y=200-length*Math.sin(a);ctx.beginPath();ctx.moveTo(210,200);ctx.lineTo(x,y);ctx.stroke();ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x-16*Math.cos(a+.45),y+16*Math.sin(a+.45));ctx.moveTo(x,y);ctx.lineTo(x-16*Math.cos(a-.45),y+16*Math.sin(a-.45));ctx.stroke()}arrow(d.goal,'#f6d45f',120);arrow(d.heading[i],'#50dec8',100);const rates=d.rates[Math.min(i,d.rates.length-1)],maximum=120;ctx.fillStyle='#91baff';rates.forEach((r,k)=>ctx.fillRect(425+k*18,350-Math.min(r/maximum,1)*230,12,Math.min(r/maximum,1)*230));ctx.font='15px system-ui';ctx.fillStyle='white';ctx.fillText('24 neuronas PFL3 · escala 0–120 Hz',425,385)}
slider.oninput=draw;scenario.onchange=()=>{slider.value=0;draw()};document.querySelector('#play').onclick=()=>{playing=!playing;if(Number(slider.value)==400)slider.value=0};function tick(t){if(playing&&t-last>=50){last=t;slider.value=Math.min(400,Number(slider.value)+1);draw();if(Number(slider.value)==400)playing=false}requestAnimationFrame(tick)}draw();requestAnimationFrame(tick);</script></html>'''
    destination=directory/'orientation-replay.html'
    destination.write_text(document.replace('__DATA__',json.dumps(data,separators=(',',':'))),encoding='utf-8')
    return destination


if __name__=='__main__':
    print(generate(Path.cwd()))
