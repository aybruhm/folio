from datetime import date
from typing import List, Optional, Tuple


class PerformanceService:
    @staticmethod
    def calculate_twr(
        beginning_value: float,
        ending_value: float,
        cash_flows: List[Tuple[date, float]],
        start_date: date,
        end_date: date,
    ) -> float:
        """
        Calculate Time-Weighted Return using Modified Dietz method.
        Returns: float (e.g., 0.15 = 15% return)
        """
        if not cash_flows:
            if beginning_value == 0:
                return 0.0
            return (ending_value - beginning_value) / beginning_value

        cash_flows = sorted(cash_flows, key=lambda x: x[0])
        total_days = (end_date - start_date).days

        if total_days == 0:
            return 0.0

        weighted_cash_flows = 0.0
        for flow_date, flow_amount in cash_flows:
            days_remaining = (end_date - flow_date).days
            weight = days_remaining / total_days
            weighted_cash_flows += flow_amount * weight

        total_cash_flows = sum(flow[1] for flow in cash_flows)
        denominator = beginning_value + weighted_cash_flows

        if denominator == 0:
            return 0.0

        return (ending_value - beginning_value - total_cash_flows) / denominator

    @staticmethod
    def calculate_mwr(
        beginning_value: float,
        ending_value: float,
        cash_flows: List[Tuple[date, float]],
        start_date: date,
        end_date: date,
    ) -> float:
        """
        Calculate Money-Weighted Return (IRR) using Newton-Raphson method.
        Returns: float (e.g., 0.15 = 15% return)
        """
        if not cash_flows:
            if beginning_value == 0:
                return 0.0
            return (ending_value - beginning_value) / beginning_value

        def npv(rate: float) -> float:
            total = -beginning_value
            for flow_date, flow_amount in cash_flows:
                days_diff = (flow_date - start_date).days
                years_diff = days_diff / 365.25
                # Negate: IRR uses investor-centric convention (buys are outflows)
                total += (-flow_amount) / ((1 + rate) ** years_diff)

            days_end = (end_date - start_date).days
            years_end = days_end / 365.25
            total += ending_value / ((1 + rate) ** years_end)
            return total

        rate = 0.1
        for _ in range(100):
            try:
                npv_val = npv(rate)
                if abs(npv_val) < 0.01:
                    break
                delta = 0.0001
                derivative = (npv(rate + delta) - npv_val) / delta
                if abs(derivative) < 1e-10:
                    break
                rate = rate - npv_val / derivative
                rate = max(-0.9999, min(rate, 5.0))
            except Exception:
                break

        if not (-0.9999 <= rate <= 5.0):
            total_flows = sum(abs(f[1]) for f in cash_flows)
            return (
                (ending_value - total_flows) / total_flows if total_flows > 0 else 0.0
            )
        return rate


class AllocationService:
    @staticmethod
    def group_by_attribute(holdings: List[dict], attribute: str) -> List[dict]:
        """
        Group holdings by specified attribute.
        Returns list of {name, value, weight_percent}
        """
        groups: dict[str, float] = {}
        total_value = 0.0

        for holding in holdings:
            group_name = holding.get(attribute, "Unknown")
            value = float(holding["market_value"])

            if group_name not in groups:
                groups[group_name] = 0.0

            groups[group_name] += value
            total_value += value

        result = []
        for name, value in sorted(groups.items(), key=lambda x: x[1], reverse=True):
            weight = round(value / total_value * 100, 2) if total_value > 0 else 0.0
            result.append({"name": name, "value": value, "weight_percent": weight})

        return result


class FIREService:
    @staticmethod
    def calculate_future_value(
        present_value: float, monthly_savings: float, annual_return: float, months: int
    ) -> float:
        """
        Calculate future value with monthly compounding.
        Formula: FV = PV × (1 + r)^n + PMT × [((1+r)^n - 1) / r]
        """
        monthly_rate = annual_return / 12

        if monthly_rate == 0:
            return present_value + (monthly_savings * months)

        factor = (1 + monthly_rate) ** months
        fv = present_value * factor
        fv += monthly_savings * ((factor - 1) / monthly_rate)

        return fv

    @staticmethod
    def calculate_projection(
        current_value: float,
        target_value: float,
        monthly_savings: float,
        annual_return: float,
        target_months: int,
    ) -> dict:
        """
        Calculate FIRE projection to target date.
        """
        monthly_rate = annual_return / 12

        if monthly_rate == 0:
            months_needed = (
                (target_value - current_value) / monthly_savings
                if monthly_savings > 0
                else None
            )
            projected = current_value + (monthly_savings * target_months)
            return {
                "months_to_target": int(months_needed)
                if months_needed is not None
                else None,
                "projected_value": projected,
                "shortfall": max(0.0, target_value - projected),
                "progress_percent": round(current_value / target_value * 100, 2)
                if target_value > 0
                else 0.0,
            }

        projected_value = FIREService.calculate_future_value(
            current_value, monthly_savings, annual_return, target_months
        )

        shortfall = max(0.0, target_value - projected_value)
        progress = (
            round(current_value / target_value * 100, 2) if target_value > 0 else 0.0
        )

        return {
            "projected_value": projected_value,
            "shortfall": shortfall,
            "progress_percent": progress,
            "will_reach_target": projected_value >= target_value,
        }

    @staticmethod
    def calculate_required_return(
        current_value: float,
        target_value: float,
        monthly_savings: float,
        target_months: int,
    ) -> Optional[float]:
        """
        Calculate required annual return to hit target given current savings.
        Uses Newton-Raphson approximation.
        """
        if current_value >= target_value:
            return 0.0

        def target_delta(annual_rate: float) -> float:
            fv = FIREService.calculate_future_value(
                current_value, monthly_savings, annual_rate, target_months
            )
            return fv - target_value

        rate = 0.07
        for _ in range(100):
            delta = target_delta(rate)
            if abs(delta) < 0.01:
                break

            derivative = (target_delta(rate + 0.00001) - delta) / 0.00001
            if derivative == 0:
                break

            rate = rate - delta / derivative

            if rate < 0:
                return None

        return rate if rate >= 0 else None
