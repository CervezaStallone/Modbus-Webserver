"""
Data Aggregator voor het berekenen van aggregaties van TrendData.
"""
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Min, Max, Avg, Count
from ..models import Register, TrendData, TrendDataAggregated

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Berekent en slaat aggregaties op van trend data.
    """
    
    def aggregate_hourly(self, register: Register, start_time: datetime = None) -> int:
        """
        Bereken hourly aggregatie voor een register.
        
        Args:
            register: Register object
            start_time: Start tijd voor aggregatie (default: vorig uur)
            
        Returns:
            Aantal aangemaakte aggregatie records
        """
        if start_time is None:
            # Neem vorig uur (afgerond)
            now = timezone.now()
            start_time = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
        
        end_time = start_time + timedelta(hours=1)
        
        # Haal raw data op
        data = TrendData.objects.filter(
            register=register,
            timestamp__gte=start_time,
            timestamp__lt=end_time,
            quality='good'
        )
        
        if not data.exists():
            logger.debug(f"Geen data voor {register.name} tussen {start_time} en {end_time}")
            return 0
        
        # Bereken aggregaties
        aggregates = data.aggregate(
            min_value=Min('converted_value'),
            max_value=Max('converted_value'),
            avg_value=Avg('converted_value'),
            sample_count=Count('id')
        )
        
        # Sla op (of update bestaande)
        agg, created = TrendDataAggregated.objects.update_or_create(
            register=register,
            interval='hourly',
            timestamp=start_time,
            defaults={
                'min_value': aggregates['min_value'],
                'max_value': aggregates['max_value'],
                'avg_value': aggregates['avg_value'],
                'sample_count': aggregates['sample_count']
            }
        )
        
        action = 'created' if created else 'updated'
        logger.info(
            f"Hourly aggregation {action} for {register.name} at {start_time}: "
            f"min={aggregates['min_value']}, max={aggregates['max_value']}, "
            f"avg={aggregates['avg_value']:.2f}, samples={aggregates['sample_count']}"
        )
        
        return 1
    
    def aggregate_daily(self, register: Register, start_time: datetime = None) -> int:
        """
        Bereken daily aggregatie voor een register (van hourly data).
        
        Args:
            register: Register object
            start_time: Start tijd voor aggregatie (default: gisteren)
            
        Returns:
            Aantal aangemaakte aggregatie records
        """
        if start_time is None:
            # Neem gisteren (00:00)
            now = timezone.now()
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        
        end_time = start_time + timedelta(days=1)
        
        # Haal hourly aggregaties op
        hourly_data = TrendDataAggregated.objects.filter(
            register=register,
            interval='hourly',
            timestamp__gte=start_time,
            timestamp__lt=end_time
        )
        
        if not hourly_data.exists():
            logger.debug(f"Geen hourly data voor {register.name} voor {start_time.date()}")
            return 0
        
        # Bereken aggregaties van hourly data
        aggregates = hourly_data.aggregate(
            min_value=Min('min_value'),
            max_value=Max('max_value'),
            avg_value=Avg('avg_value'),
            sample_count=Count('id')
        )
        
        # Sla op (of update bestaande)
        agg, created = TrendDataAggregated.objects.update_or_create(
            register=register,
            interval='daily',
            timestamp=start_time,
            defaults={
                'min_value': aggregates['min_value'],
                'max_value': aggregates['max_value'],
                'avg_value': aggregates['avg_value'],
                'sample_count': aggregates['sample_count']
            }
        )
        
        action = 'created' if created else 'updated'
        logger.info(
            f"Daily aggregation {action} for {register.name} at {start_time.date()}: "
            f"min={aggregates['min_value']}, max={aggregates['max_value']}, "
            f"avg={aggregates['avg_value']:.2f}"
        )
        
        return 1
    
    def aggregate_weekly(self, register: Register, start_time: datetime = None) -> int:
        """
        Bereken weekly aggregatie voor een register (van daily data).
        
        Args:
            register: Register object
            start_time: Start tijd voor aggregatie (default: vorige week maandag)
            
        Returns:
            Aantal aangemaakte aggregatie records
        """
        if start_time is None:
            # Neem vorige week maandag
            now = timezone.now()
            days_since_monday = now.weekday()
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(
                days=days_since_monday + 7
            )
        
        end_time = start_time + timedelta(days=7)
        
        # Haal daily aggregaties op
        daily_data = TrendDataAggregated.objects.filter(
            register=register,
            interval='daily',
            timestamp__gte=start_time,
            timestamp__lt=end_time
        )
        
        if not daily_data.exists():
            logger.debug(f"Geen daily data voor {register.name} voor week {start_time.date()}")
            return 0
        
        # Bereken aggregaties van daily data
        aggregates = daily_data.aggregate(
            min_value=Min('min_value'),
            max_value=Max('max_value'),
            avg_value=Avg('avg_value'),
            sample_count=Count('id')
        )
        
        # Sla op (of update bestaande)
        agg, created = TrendDataAggregated.objects.update_or_create(
            register=register,
            interval='weekly',
            timestamp=start_time,
            defaults={
                'min_value': aggregates['min_value'],
                'max_value': aggregates['max_value'],
                'avg_value': aggregates['avg_value'],
                'sample_count': aggregates['sample_count']
            }
        )
        
        action = 'created' if created else 'updated'
        logger.info(
            f"Weekly aggregation {action} for {register.name} at {start_time.date()}: "
            f"min={aggregates['min_value']}, max={aggregates['max_value']}, "
            f"avg={aggregates['avg_value']:.2f}"
        )
        
        return 1
    
    def aggregate_all_registers(self, aggregation_type: str = 'hourly') -> dict:
        """
        Voer aggregatie uit voor alle enabled registers.
        
        Args:
            aggregation_type: Type aggregatie ('hourly', 'daily', 'weekly')
            
        Returns:
            Dict met statistieken
        """
        registers = Register.objects.filter(enabled=True)
        
        total_processed = 0
        total_errors = 0
        
        for register in registers:
            try:
                if aggregation_type == 'hourly':
                    count = self.aggregate_hourly(register)
                elif aggregation_type == 'daily':
                    count = self.aggregate_daily(register)
                elif aggregation_type == 'weekly':
                    count = self.aggregate_weekly(register)
                else:
                    logger.error(f"Onbekend aggregation type: {aggregation_type}")
                    continue
                
                total_processed += count
                
            except Exception as e:
                logger.error(f"Fout bij aggregeren van {register.name}: {e}")
                total_errors += 1
        
        logger.info(
            f"{aggregation_type.capitalize()} aggregation voltooid: "
            f"{total_processed} records verwerkt, {total_errors} errors"
        )
        
        return {
            'processed': total_processed,
            'errors': total_errors,
            'register_count': registers.count()
        }
    
    def cleanup_old_data(self, raw_data_days: int = 7, hourly_data_days: int = 90, 
                        daily_data_days: int = 730) -> dict:
        """
        Verwijder oude data volgens retention policy.
        
        Args:
            raw_data_days: Bewaar raw data voor N dagen
            hourly_data_days: Bewaar hourly aggregaties voor N dagen
            daily_data_days: Bewaar daily aggregaties voor N dagen
            
        Returns:
            Dict met cleanup statistieken
        """
        now = timezone.now()
        
        # Cleanup raw data
        raw_cutoff = now - timedelta(days=raw_data_days)
        raw_deleted = TrendData.objects.filter(timestamp__lt=raw_cutoff).delete()
        
        # Cleanup hourly aggregaties
        hourly_cutoff = now - timedelta(days=hourly_data_days)
        hourly_deleted = TrendDataAggregated.objects.filter(
            interval='hourly',
            timestamp__lt=hourly_cutoff
        ).delete()
        
        # Cleanup daily aggregaties
        daily_cutoff = now - timedelta(days=daily_data_days)
        daily_deleted = TrendDataAggregated.objects.filter(
            interval='daily',
            timestamp__lt=daily_cutoff
        ).delete()
        
        logger.info(
            f"Data cleanup voltooid: "
            f"Raw: {raw_deleted[0]} records, "
            f"Hourly: {hourly_deleted[0]} records, "
            f"Daily: {daily_deleted[0]} records"
        )
        
        return {
            'raw_deleted': raw_deleted[0],
            'hourly_deleted': hourly_deleted[0],
            'daily_deleted': daily_deleted[0]
        }
