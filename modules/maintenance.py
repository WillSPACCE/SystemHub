import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from modules.cleaner import CleanupManager
from modules.email_service import ResendEmailService, build_email_body
from modules.history import HistoryManager
from modules.report import ReportGenerator


class MaintenanceCoordinator:
    def __init__(self, cleaner: Optional[CleanupManager] = None, report_generator: Optional[ReportGenerator] = None, history_manager: Optional[HistoryManager] = None, email_service: Optional[ResendEmailService] = None):
        self.cleaner = cleaner or CleanupManager()
        self.report_generator = report_generator or ReportGenerator()
        self.history_manager = history_manager or HistoryManager()
        self.email_service = email_service or ResendEmailService()

    def get_action_labels(self) -> List[Dict[str, Any]]:
        return self.cleaner.get_default_actions()

    def run_maintenance(
        self,
        selected_ids: Optional[List[str]] = None,
        initial_payload: Optional[Dict[str, Any]] = None,
        final_payload: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Any] = None,
        selected_programs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        started_at = time.perf_counter()
        settings = settings or {}
        if progress_callback:
            progress_callback("Coletando informações", "running", "Coletando dados iniciais do sistema...", 5)
        initial_payload = initial_payload or {}
        if not initial_payload:
            initial_payload = self._gather_payload()

        if progress_callback:
            progress_callback("Limpando arquivos", "running", "Iniciando limpeza selecionada...", 15)
        cleanup_results = self.cleaner.run_cleanup(selected_ids=selected_ids, progress_callback=progress_callback)
        recovered_bytes = sum(item.get("freed_bytes", 0) for item in cleanup_results if isinstance(item, dict))

        if progress_callback:
            progress_callback("Defender", "running", "Executando verificação rápida do Microsoft Defender...", 45)
        defender_result = self._run_defender_check()
        if defender_result:
            cleanup_results.append(defender_result)
            if defender_result.get("status") == "OK":
                recovered_bytes += 0

        if progress_callback:
            progress_callback("Atualizando informações", "running", "Coletando dados finais após a limpeza...", 70)
        final_payload = final_payload or self._gather_payload()

        if progress_callback:
            progress_callback("Gerando relatório", "running", "Montando relatório técnico...", 85)
        report_path = self.report_generator.write_report(
            title="INFOCASE CHECKUP",
            initial_payload=initial_payload,
            final_payload=final_payload,
            cleanup_results=cleanup_results,
            recovered_bytes=recovered_bytes,
            maintenance_duration=self._format_duration(time.perf_counter() - started_at),
            overall_status="OK",
            selected_programs=selected_programs or [],
        )

        sent = False
        send_error = None
        if settings.get("auto_send", False):
            if progress_callback:
                progress_callback("Enviando relatório", "running", "Enviando relatório por e-mail...", 95)
            try:
                recipient = settings.get("recipient_email")
                api_key = settings.get("resend_api_key")
                from_email = settings.get("from_email") or getattr(self.email_service, "from_email", None)
                if recipient and api_key:
                    self.email_service.api_key = api_key
                    if from_email:
                        self.email_service.from_email = from_email
                    generate_subject = getattr(self.email_service, "generate_subject", None)
                    subject = (
                        generate_subject(initial_payload.get("system", {}).get("computer_name", "Sistema"))
                        if callable(generate_subject)
                        else f"Relatório de Manutenção - {initial_payload.get('system', {}).get('computer_name', 'Sistema')}"
                    )
                    result = self.email_service.send_report(
                        recipient_email=recipient,
                        subject=subject,
                        body=build_email_body(initial_payload, report_path, recovered_bytes),
                        attachment_path=report_path,
                    )
                    sent = bool(result.get("success", False))
                    send_error = None if sent else result.get("message", "Falha ao enviar o relatório.")
                else:
                    send_error = "Configuração incompleta para envio por e-mail."
            except Exception as exc:
                send_error = str(exc)

        history_record = {
            "status": "OK" if not send_error else "⚠",
            "report_path": report_path,
            "sent": sent,
            "recovered_bytes": recovered_bytes,
            "duration": self._format_duration(time.perf_counter() - started_at),
            "error": send_error,
        }
        self.history_manager.append(history_record)

        if progress_callback:
            progress_callback("Concluído", "done", "Manutenção concluída com sucesso.", 100)
        return {
            "report_path": report_path,
            "cleanup_results": cleanup_results,
            "recovered_bytes": recovered_bytes,
            "duration": self._format_duration(time.perf_counter() - started_at),
            "sent": sent,
            "error": send_error,
            "history_record": history_record,
        }

    def test_send(self, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        settings = settings or {}
        self.email_service.api_key = settings.get("resend_api_key")
        if settings.get("from_email"):
            self.email_service.from_email = settings.get("from_email")
        self.email_service.recipient_email = settings.get("recipient_email", "")
        return self.email_service.test_send(
            recipient_email=settings.get("recipient_email", ""),
            initial_payload={"system": {"computer_name": "PC-TEST", "os_name": "Windows", "version": "11"}},
        )

    def _gather_payload(self) -> Dict[str, Any]:
        from modules.collector_service import HardwareCollectorService
        collector = HardwareCollectorService()
        return collector.collect()

    def _run_defender_check(self) -> Dict[str, Any]:
        try:
            if os.name != "nt":
                return {"id": "defender", "name": "Microsoft Defender", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Defender não disponível neste ambiente."}
            result = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "(Get-MpComputerStatus).AntivirusEnabled"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            if result.returncode != 0:
                return {"id": "defender", "name": "Microsoft Defender", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Falha ao consultar Defender."}
            enabled = str(result.stdout).strip().lower() == "true"
            if not enabled:
                return {"id": "defender", "name": "Microsoft Defender", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Microsoft Defender desativado."}
            subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Start-MpScan -ScanType QuickScan"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return {"id": "defender", "name": "Microsoft Defender", "status": "OK", "freed_bytes": 0, "freed": "0 B", "message": "Verificação rápida concluída."}
        except Exception:
            return {"id": "defender", "name": "Microsoft Defender", "status": "⚠", "freed_bytes": 0, "freed": "0 B", "message": "Falha ao executar Defender."}

    @staticmethod
    def _format_duration(seconds: float) -> str:
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
