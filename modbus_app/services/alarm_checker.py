"""
Alarm Checker voor het evalueren van alarm condities.
"""
import logging
from datetime import datetime
from django.utils import timezone
from ..models import Alarm, AlarmHistory, Register, TrendData

logger = logging.getLogger(__name__)


class AlarmChecker:
    """
    Evalueert alarm condities en triggert/cleared alarms.
    """
    
    def check_alarm(self, alarm: Alarm) -> bool:
        """
        Check een enkel alarm.
        
        Args:
            alarm: Alarm object om te checken
            
        Returns:
            True als alarm getriggerd werd, False anders
        """
        if not alarm.enabled:
            return False
        
        # Haal laatste waarde op van het register
        latest_data = TrendData.objects.filter(
            register=alarm.register,
            quality='good'
        ).order_by('-timestamp').first()
        
        if not latest_data:
            logger.debug(f"Geen data beschikbaar voor alarm {alarm.name}")
            return False
        
        value = latest_data.value
        
        # Evalueer conditie
        should_trigger = self._evaluate_condition(
            alarm.condition,
            value,
            alarm.threshold_high,
            alarm.threshold_low,
            alarm.hysteresis
        )
        
        # Check of alarm status moet wijzigen
        if should_trigger and not alarm.is_active():
            # Trigger alarm
            self._trigger_alarm(alarm, value)
            return True
        elif not should_trigger and alarm.is_active():
            # Clear alarm
            self._clear_alarm(alarm, value)
        
        return False
    
    def _evaluate_condition(self, condition: str, value: float, 
                           threshold_high: float, threshold_low: float = None,
                           hysteresis: float = 0.0) -> bool:
        """
        Evalueer alarm conditie.
        
        Args:
            condition: Conditie type
            value: Huidige waarde
            threshold_high: Hoge threshold
            threshold_low: Lage threshold (voor range)
            hysteresis: Hysteresis waarde
            
        Returns:
            True als conditie voldaan is, False anders
        """
        if condition == 'greater_than':
            return value > (threshold_high + hysteresis)
        
        elif condition == 'less_than':
            return value < (threshold_high - hysteresis)
        
        elif condition == 'equals':
            # Voor equals gebruiken we hysteresis als tolerance
            return abs(value - threshold_high) <= hysteresis
        
        elif condition == 'not_equals':
            return abs(value - threshold_high) > hysteresis
        
        elif condition == 'range':
            # Binnen range (low <= value <= high)
            if threshold_low is None:
                logger.error(f"range conditie vereist threshold_low")
                return False
            return not (threshold_low - hysteresis <= value <= threshold_high + hysteresis)
        
        else:
            logger.error(f"Onbekende conditie: {condition}")
            return False
    
    def _trigger_alarm(self, alarm: Alarm, value: float):
        """
        Trigger een alarm.
        
        Args:
            alarm: Alarm object
            value: Waarde die het alarm triggerde
        """
        # Update alarm status
        alarm.last_triggered = timezone.now()
        alarm.save(update_fields=['last_triggered'])
        
        # Maak alarm history entry
        AlarmHistory.objects.create(
            alarm=alarm,
            triggered_at=timezone.now(),
            trigger_value=value,
            acknowledged=False
        )
        
        logger.warning(
            f"ALARM TRIGGERED: {alarm.name} "
            f"(Register: {alarm.register.name}, Value: {value}, "
            f"Severity: {alarm.severity})"
        )
        
        # Hier zou je notificaties kunnen versturen (email, webhook, etc.)
        # Voor nu loggen we alleen
    
    def _clear_alarm(self, alarm: Alarm, value: float):
        """
        Clear een alarm.
        
        Args:
            alarm: Alarm object
            value: Waarde waarbij het alarm cleared
        """
        # Vind actieve alarm history entry
        active_history = AlarmHistory.objects.filter(
            alarm=alarm,
            cleared_at__isnull=True
        ).order_by('-triggered_at').first()
        
        if active_history:
            active_history.cleared_at = timezone.now()
            active_history.save(update_fields=['cleared_at'])
        
        logger.info(
            f"ALARM CLEARED: {alarm.name} "
            f"(Register: {alarm.register.name}, Value: {value})"
        )
    
    def check_all_alarms(self) -> dict:
        """
        Check alle enabled alarms.
        
        Returns:
            Dict met statistieken
        """
        alarms = Alarm.objects.filter(enabled=True).select_related('register')
        
        total_checked = 0
        total_triggered = 0
        total_errors = 0
        
        for alarm in alarms:
            try:
                triggered = self.check_alarm(alarm)
                total_checked += 1
                if triggered:
                    total_triggered += 1
                    
            except Exception as e:
                logger.error(f"Fout bij checken alarm {alarm.name}: {e}")
                total_errors += 1
        
        logger.debug(
            f"Alarm check voltooid: {total_checked} alarms gechecked, "
            f"{total_triggered} getriggerd, {total_errors} errors"
        )
        
        return {
            'checked': total_checked,
            'triggered': total_triggered,
            'errors': total_errors
        }
    
    def get_active_alarms(self) -> list:
        """
        Haal alle actieve alarms op.
        
        Returns:
            List van AlarmHistory objecten voor actieve alarms
        """
        return AlarmHistory.objects.filter(
            cleared_at__isnull=True,
            alarm__enabled=True
        ).select_related('alarm', 'alarm__register').order_by('-triggered_at')
    
    def acknowledge_alarm(self, alarm_history_id: int, acknowledged_by: str = None) -> bool:
        """
        Bevestig een alarm.
        
        Args:
            alarm_history_id: ID van AlarmHistory entry
            acknowledged_by: Gebruiker die alarm bevestigde
            
        Returns:
            True als succesvol, False anders
        """
        try:
            history = AlarmHistory.objects.get(id=alarm_history_id)
            
            if history.acknowledged:
                logger.warning(f"Alarm {alarm_history_id} is al bevestigd")
                return False
            
            history.acknowledged = True
            history.acknowledged_at = timezone.now()
            history.acknowledged_by = acknowledged_by or 'system'
            history.save(update_fields=['acknowledged', 'acknowledged_at', 'acknowledged_by'])
            
            logger.info(f"Alarm {history.alarm.name} bevestigd door {acknowledged_by}")
            return True
            
        except AlarmHistory.DoesNotExist:
            logger.error(f"AlarmHistory {alarm_history_id} niet gevonden")
            return False
        except Exception as e:
            logger.error(f"Fout bij bevestigen alarm: {e}")
            return False
