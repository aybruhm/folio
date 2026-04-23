from decimal import Decimal, ROUND_HALF_UP
from datetime import date, timedelta
from typing import List, Optional, Tuple
from domain.value_objects.money import Money, Currency

class PerformanceService:
    @staticmethod
    def calculate_twr(
        beginning_value: Decimal,
        ending_value: Decimal,
        cash_flows: List[Tuple[date, Decimal]],
        start_date: date,
        end_date: date
    ) -> Decimal:
        """
        Calculate Time-Weighted Return using Modified Dietz method.
        Returns: decimal (e.g., 0.15 = 15% return)
        """
        if not cash_flows:
            if beginning_value == 0:
                return Decimal('0')
            return (ending_value - beginning_value) / beginning_value
        
        cash_flows = sorted(cash_flows, key=lambda x: x[0])
        total_days = (end_date - start_date).days
        
        if total_days == 0:
            return Decimal('0')
        
        weighted_cash_flows = Decimal('0')
        for flow_date, flow_amount in cash_flows:
            days_remaining = (end_date - flow_date).days
            weight = Decimal(days_remaining) / Decimal(total_days)
            weighted_cash_flows += flow_amount * weight
        
        total_cash_flows = sum(flow[1] for flow in cash_flows)
        denominator = beginning_value + weighted_cash_flows
        
        if denominator == 0:
            return Decimal('0')
        
        return (ending_value - beginning_value - total_cash_flows) / denominator
    
    @staticmethod
    def calculate_mwr(
        beginning_value: Decimal,
        ending_value: Decimal,
        cash_flows: List[Tuple[date, Decimal]],
        start_date: date,
        end_date: date
    ) -> Decimal:
        """
        Calculate Money-Weighted Return (IRR) using Newton-Raphson method.
        Returns: decimal (e.g., 0.15 = 15% return)
        """
        if not cash_flows:
            if beginning_value == 0:
                return Decimal('0')
            return (ending_value - beginning_value) / beginning_value
        
        def npv(rate: Decimal) -> Decimal:
            total = -beginning_value
            for flow_date, flow_amount in cash_flows:
                days_diff = (flow_date - start_date).days
                years_diff = Decimal(days_diff) / Decimal('365.25')
                total += flow_amount / ((1 + rate) ** years_diff)
            
            days_end = (end_date - start_date).days
            years_end = Decimal(days_end) / Decimal('365.25')
            total += ending_value / ((1 + rate) ** years_end)
            return total
        
        rate = Decimal('0.1')
        for _ in range(100):
            try:
                npv_val = npv(rate)
                if abs(npv_val) < Decimal('0.001'): 
                    break
                delta = Decimal('0.0001')
                derivative = (npv(rate + delta) - npv_val) / delta
                if abs(derivative) < Decimal('1e-10'): 
                    break
                rate = rate - npv_val / derivative
                rate = max(Decimal('-0.9999'), min(rate, Decimal('5')))
            except Exception:
                break
        
        if not (Decimal('-0.9999') <= rate <= Decimal('5')):
            total_flows = sum(abs(f[1]) for f in cash_flows)
            return (ending_value - total_flows) / total_flows if total_flows > 0 else Decimal('0')
        return rate

class AllocationService:
    @staticmethod
    def group_by_attribute(
        holdings: List[dict],
        attribute: str
    ) -> List[dict]:
        """
        Group holdings by specified attribute (asset_class, sector, industry, country, currency, ticker).
        Returns list of {name, value, weight_percent}
        """
        groups = {}
        total_value = Decimal('0')
        
        for holding in holdings:
            group_name = holding.get(attribute, 'Unknown')
            value = holding['market_value']
            
            if group_name not in groups:
                groups[group_name] = Decimal('0')
            
            groups[group_name] += value
            total_value += value
        
        result = []
        for name, value in sorted(groups.items(), key=lambda x: x[1], reverse=True):
            weight = (value / total_value * Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            ) if total_value > 0 else Decimal('0')
            
            result.append({
                'name': name,
                'value': value,
                'weight_percent': weight
            })
        
        return result

class FIREService:
    @staticmethod
    def calculate_future_value(
        present_value: Decimal,
        monthly_savings: Decimal,
        annual_return: Decimal,
        months: int
    ) -> Decimal:
        """
        Calculate future value with monthly compounding.
        Formula: FV = PV × (1 + r)^n + PMT × [((1+r)^n - 1) / r]
        """
        monthly_rate = annual_return / Decimal('12')
        
        if monthly_rate == 0:
            return present_value + (monthly_savings * Decimal(months))
        
        factor = (1 + monthly_rate) ** months
        fv = present_value * factor
        fv += monthly_savings * ((factor - 1) / monthly_rate)
        
        return fv
    
    @staticmethod
    def calculate_projection(
        current_value: Decimal,
        target_value: Decimal,
        monthly_savings: Decimal,
        annual_return: Decimal,
        target_months: int
    ) -> dict:
        """
        Calculate FIRE projection to target date.
        """
        monthly_rate = annual_return / Decimal('12')
        
        if monthly_rate == 0:
            months_needed = (target_value - current_value) / monthly_savings
            return {
                'months_to_target': int(months_needed) if monthly_savings > 0 else None,
                'projected_value': current_value + (monthly_savings * Decimal(target_months)),
                'shortfall': max(Decimal('0'), target_value - (current_value + monthly_savings * Decimal(target_months))),
                'progress_percent': (current_value / target_value * Decimal('100')).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            }
        
        projected_value = FIREService.calculate_future_value(
            current_value, monthly_savings, annual_return, target_months
        )
        
        shortfall = max(Decimal('0'), target_value - projected_value)
        progress = (current_value / target_value * Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        return {
            'projected_value': projected_value,
            'shortfall': shortfall,
            'progress_percent': progress,
            'will_reach_target': projected_value >= target_value
        }
    
    @staticmethod
    def calculate_required_return(
        current_value: Decimal,
        target_value: Decimal,
        monthly_savings: Decimal,
        target_months: int
    ) -> Optional[Decimal]:
        """
        Calculate required annual return to hit target given current savings.
        Uses Newton-Raphson approximation.
        """
        if current_value >= target_value:
            return Decimal('0')
        
        def target_delta(annual_rate: Decimal) -> Decimal:
            fv = FIREService.calculate_future_value(
                current_value, monthly_savings, annual_rate, target_months
            )
            return fv - target_value
        
        rate = Decimal('0.07')
        for _ in range(100):
            delta = target_delta(rate)
            if abs(delta) < Decimal('0.01'):
                break
            
            derivative = (target_delta(rate + Decimal('0.00001')) - delta) / Decimal('0.00001')
            if derivative == 0:
                break
            
            rate = rate - delta / derivative
            
            if rate < 0:
                return None
        
        return rate if rate >= 0 else None
