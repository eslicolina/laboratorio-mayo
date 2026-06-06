/* ═══════════════════════════════════════════
   Smart Gate AI — Logs en tiempo real
   ═══════════════════════════════════════════ */

(function () {
  'use strict';

  const table = document.getElementById('logsTable');
  const logCount = document.getElementById('logCount');
  const connectionDot = document.getElementById('connectionDot');
  const connectionStatus = document.getElementById('connectionStatus');

  const ESTADOS_CRITICOS = ['Intruso', 'Anomalía', 'intruso', 'anomalía'];

  function esEstadoCritico(estado) {
    return ESTADOS_CRITICOS.includes(estado);
  }

  function formatearFecha(fechaStr) {
    if (!fechaStr) return '\u2014';
    try {
      const date = new Date(fechaStr);
      if (isNaN(date.getTime())) return fechaStr;
      const hoy = new Date();
      const esHoy = date.toDateString() === hoy.toDateString();
      if (esHoy) {
        return date.toLocaleTimeString('es-MX', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        });
      }
      return date.toLocaleDateString('es-MX', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch (_) {
      return fechaStr;
    }
  }

  async function cargarLogs() {
    try {
      const response = await fetch('/api/logs');

      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }

      const logs = await response.json();

      connectionDot.className = 'w-1.5 h-1.5 rounded-full bg-green-500';
      connectionStatus.textContent = 'Conectado';
      connectionStatus.className = 'font-mono text-green-400';

      if (!logs || logs.length === 0) {
        table.innerHTML =
          '<tr>' +
          '<td colspan="6" class="px-4 py-8 text-center text-gray-600 text-sm">' +
          '<span class="block mb-1">\uD83D\uDCE1</span>' +
          'No hay registros de acceso a\u00fan.' +
          '</td>' +
          '</tr>';
        logCount.textContent = '0';
        return;
      }

      logCount.textContent = logs.length;

      const fragment = document.createDocumentFragment();

      logs.forEach(function (log, index) {
        const estado = log.estado || 'Normal';
        const esCritico = esEstadoCritico(estado);
        const confianza = Number(log.confianza) || 0;

        const row = document.createElement('tr');

        if (esCritico) {
          row.className = 'row-critical border-l-3';
        } else {
          row.className =
            'hover:bg-slate-800/40 transition duration-150';
          if (index % 2 === 0) {
            row.classList.add('bg-slate-800/20');
          }
        }

        var confianzaClase = 'text-green-400';
        if (confianza < 80 && confianza >= 50) {
          confianzaClase = 'text-yellow-400';
        } else if (confianza < 50) {
          confianzaClase = 'text-red-400';
        }

        row.innerHTML =
          '<td class="px-3 md:px-4 py-2.5 md:py-3 font-mono text-gray-400 text-[0.65rem] md:text-xs">' +
          (log.id ?? '\u2014') +
          '</td>' +
          '<td class="px-3 md:px-4 py-2.5 md:py-3 font-medium text-gray-200">' +
          (log.usuario ?? '\u2014') +
          '</td>' +
          '<td class="px-3 md:px-4 py-2.5 md:py-3 text-gray-300">' +
          (log.ubicacion ?? '\u2014') +
          '</td>' +
          '<td class="px-3 md:px-4 py-2.5 md:py-3 text-center font-mono">' +
          '<span class="' + confianzaClase + ' font-semibold tabular-nums">' +
          confianza + '%' +
          '</span>' +
          '</td>' +
          '<td class="px-3 md:px-4 py-2.5 md:py-3 text-center">' +
          '<span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[0.65rem] md:text-xs font-bold tracking-wide ' +
          (esCritico
            ? 'bg-red-500/15 text-red-300 border border-red-500/30 animate-pulse'
            : 'bg-green-500/10 text-green-300 border border-green-500/20') +
          '">' +
          (estado === 'Intruso' || estado === 'Anomal\u00eda'
            ? '\u26A0 ' + estado
            : '\u2713 ' + estado) +
          '</span>' +
          '</td>' +
          '<td class="px-3 md:px-4 py-2.5 md:py-3 text-gray-500 whitespace-nowrap font-mono text-[0.6rem] md:text-[0.65rem]">' +
          formatearFecha(log.fecha) +
          '</td>';

        fragment.appendChild(row);
      });

      table.innerHTML = '';
      table.appendChild(fragment);
    } catch (error) {
      console.error('[SmartGate] Error cargando logs:', error);

      connectionDot.className = 'w-1.5 h-1.5 rounded-full bg-red-500';
      connectionStatus.textContent = 'Desconectado';
      connectionStatus.className = 'font-mono text-red-400';

      if (table.children.length === 0) {
        table.innerHTML =
          '<tr>' +
          '<td colspan="6" class="px-4 py-8 text-center text-gray-500 text-sm">' +
          '<span class="block mb-1 text-red-400">\u26A0</span>' +
          'Error de conexi\u00f3n con el servidor.' +
          '</td>' +
          '</tr>';
      }
    }
  }

  cargarLogs();
  setInterval(cargarLogs, 2000);
})();
