import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_latest_report_path(report_dir: str) -> Optional[str]:
    if not report_dir or not os.path.isdir(report_dir):
        return None

    report_files = [
        os.path.join(report_dir, name)
        for name in os.listdir(report_dir)
        if name.startswith("Relatorio_") and name.endswith(".txt") and os.path.isfile(os.path.join(report_dir, name))
    ]
    if not report_files:
        return None
    return max(report_files, key=lambda path: os.path.getmtime(path))


def format_brazilian_date(value: Optional[datetime] = None) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            return datetime.now().strftime("%d/%m/%Y")
    return datetime.now().strftime("%d/%m/%Y")


class ReportGenerator:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "Relatorio_Limpeza"))

    def write_report(
        self,
        title: str,
        initial_payload: Optional[Dict[str, Any]],
        final_payload: Optional[Dict[str, Any]],
        cleanup_results: List[Dict[str, Any]],
        recovered_bytes: int,
        maintenance_duration: str,
        overall_status: str,
        observations: Optional[List[str]] = None,
        report_name: Optional[str] = None,
        selected_programs: Optional[List[str]] = None,
    ) -> str:
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = report_name or datetime.now().strftime("%Y-%m-%d")
        report_path = os.path.join(self.output_dir, f"Relatorio_{timestamp}.txt")
        content = self._build_content(
            title=title,
            initial_payload=initial_payload or {},
            final_payload=final_payload or {},
            cleanup_results=cleanup_results,
            recovered_bytes=recovered_bytes,
            maintenance_duration=maintenance_duration,
            overall_status=overall_status,
            observations=observations or self._auto_observations(initial_payload or {}, final_payload or {}),
            selected_programs=selected_programs or [],
        )
        with open(report_path, "w", encoding="utf-8") as handle:
            handle.write(content)
        return report_path

    def _build_content(
        self,
        title: str,
        initial_payload: Dict[str, Any],
        final_payload: Dict[str, Any],
        cleanup_results: List[Dict[str, Any]],
        recovered_bytes: int,
        maintenance_duration: str,
        overall_status: str,
        observations: List[str],
        selected_programs: Optional[List[str]] = None,
    ) -> str:
        initial_system = initial_payload.get("system", {}) or {}
        final_system = final_payload.get("system", {}) or {}
        initial_cpu = initial_payload.get("cpu", {}) or {}
        final_cpu = final_payload.get("cpu", {}) or {}
        initial_memory = initial_payload.get("memory", {}) or {}
        final_memory = final_payload.get("memory", {}) or {}
        initial_disks = initial_payload.get("disks", []) or []
        final_disks = final_payload.get("disks", []) or []
        primary_disk = (final_disks[0] if final_disks else {}) or (initial_disks[0] if initial_disks else {})

        collected_at = self._read_value(initial_payload, 'collected_at', final_payload, 'collected_at', datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
        lines = [
            "==================================================",
            title,
            "RELATÓRIO DE MANUTENÇÃO",
            "==================================================",
            f"Data: {datetime.now().strftime('%Y-%m-%d')}",
            f"Hora: {datetime.now().strftime('%H:%M:%S')}",
            f"Versão do Programa: 1.0",
            f"Tempo da manutenção: {maintenance_duration}",
            f"Coleta do Dashboard: {collected_at}",
            "",
            "COMPUTADOR",
            f"Nome: {self._read_value(initial_system, 'computer_name', final_system, 'computer_name', 'Não disponível')}",
            f"Usuário: {os.environ.get('USERNAME') or os.environ.get('USER') or 'Não disponível'}",
            f"Windows: {self._read_value(initial_system, 'os_name', final_system, 'os_name', 'Não disponível')}",
            f"Build: {self._read_value(initial_system, 'build', final_system, 'build', 'Não disponível')}",
            f"Tempo Ligado: {self._read_value(initial_system, 'uptime', final_system, 'uptime', 'Não disponível')}",
            "",
            "PROCESSADOR",
            f"Modelo: {self._read_value(initial_cpu, 'name', final_cpu, 'name', 'Não disponível')}",
            f"Temperatura: {self._read_value(initial_cpu, 'temperature', final_cpu, 'temperature', 'Não disponível')}",
            f"Uso: {self._read_value(initial_cpu, 'usage', final_cpu, 'usage', 'Não disponível')}",
            f"Clock: {self._read_value(initial_cpu, 'clock_current', final_cpu, 'clock_current', 'Não disponível')}",
            f"Núcleos: {self._read_value(initial_cpu, 'physical_cores', final_cpu, 'physical_cores', 'Não disponível')}",
            f"Threads: {self._read_value(initial_cpu, 'threads', final_cpu, 'threads', 'Não disponível')}",
            "",
            "MEMÓRIA",
            f"Total: {self._read_value(initial_memory, 'total', final_memory, 'total', 'Não disponível')}",
            f"Utilizada: {self._read_value(initial_memory, 'used', final_memory, 'used', 'Não disponível')}",
            f"Livre: {self._read_value(initial_memory, 'free', final_memory, 'free', 'Não disponível')}",
            f"Uso %: {self._read_value(initial_memory, 'percent', final_memory, 'percent', 'Não disponível')}",
            "",
            "SSD",
            f"Marca: {self._read_value(primary_disk, 'manufacturer', primary_disk, 'manufacturer', 'Não disponível')}",
            f"Modelo: {self._read_value(primary_disk, 'model', primary_disk, 'model', 'Não disponível')}",
            f"Temperatura: {self._read_value(primary_disk, 'temperature', primary_disk, 'temperature', 'Não disponível')}",
            f"Saúde: {self._read_value(primary_disk, 'smart_health', primary_disk, 'smart_health', 'Não disponível')}",
            f"Espaço Livre: {self._read_value(primary_disk, 'free', primary_disk, 'free', 'Não disponível')}",
            f"Espaço Utilizado: {self._read_value(primary_disk, 'used', primary_disk, 'used', 'Não disponível')}",
            "",
            "Resumo da Limpeza",
            f"Itens processados: {len(cleanup_results)}",
            f"Espaço recuperado: {self._format_bytes(recovered_bytes)}",
            f"Status geral: {overall_status}",
            "",
        ]
        
        # Adicionar seção de aplicativos selecionados se houver
        if selected_programs:
            lines.extend([
                "APLICATIVOS SELECIONADOS",
                f"Total: {len(selected_programs)}",
            ])
            for program in selected_programs:
                lines.append(f"  • {program}")
            lines.append("")
        
        lines.extend([
            f"Espaço Recuperado: {self._format_bytes(recovered_bytes)}",
            f"Tempo da limpeza: {maintenance_duration}",
            f"Status Geral: {overall_status}",
            "",
            "OBSERVAÇÕES",
        ])
        lines.extend(observations)
        lines.extend([
            "",
            "==================================================",
            "Relatório gerado automaticamente pelo InfoCase Checkup.",
            "==================================================",
        ])
        return "\n".join(lines) + "\n"

    def _auto_observations(self, initial_payload: Dict[str, Any], final_payload: Dict[str, Any]) -> List[str]:
        cpu_data = initial_payload.get("cpu", {}) or {}
        memory_data = initial_payload.get("memory", {}) or {}
        disk_data = initial_payload.get("disks", []) or []
        primary_disk = disk_data[0] if disk_data else {}
        observations = []
        temp = cpu_data.get("temperature")
        if isinstance(temp, (int, float)) and temp >= 80:
            observations.append("Temperatura da CPU elevada.")
        else:
            observations.append("CPU trabalhando dentro do esperado.")
        percent = memory_data.get("percent")
        if isinstance(percent, str):
            try:
                value = float(percent.replace('%', ''))
            except Exception:
                value = None
        else:
            value = percent
        if isinstance(value, (int, float)) and value >= 85:
            observations.append("Uso de memória elevado.")
        else:
            observations.append("Memória disponível em nível aceitável.")
        health = primary_disk.get("smart_health")
        if isinstance(health, str) and "bom" in health.lower() or health in ("OK", "Good"):
            observations.append("SSD saudável.")
        else:
            observations.append("Saúde do SSD precisa de atenção.")
        return observations

    @staticmethod
    def _read_value(first: Dict[str, Any], first_key: str, second: Dict[str, Any], second_key: str, fallback: str) -> str:
        if first and first_key in first and first[first_key] not in (None, ""):
            return str(first[first_key])
        if second and second_key in second and second[second_key] not in (None, ""):
            return str(second[second_key])
        return fallback

    @staticmethod
    def _format_bytes(value: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(max(0, value))
        for unit in units:
            if size < 1024 or unit == units[-1]:
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} {units[-1]}"
