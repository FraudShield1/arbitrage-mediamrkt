"""
Profit Calculator for computing arbitrage ROI.

Computes ROI including shipping costs, Amazon fees, and taxes
as mentioned in the requirements.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MarketplaceEnum(str, Enum):
    """Amazon marketplace enumeration."""
    DE = "DE"
    FR = "FR"
    ES = "ES"
    IT = "IT"
    UK = "UK"


class CategoryEnum(str, Enum):
    """Product category enumeration for fee calculation."""
    ELECTRONICS = "Electronics"
    COMPUTERS = "Computers"
    VIDEO_GAMES = "Video Games"
    BOOKS = "Books"
    CLOTHING = "Clothing"
    HOME = "Home"
    HEALTH = "Health"
    SPORTS = "Sports"
    OTHER = "Other"


@dataclass
class ShippingCosts:
    """Shipping cost breakdown."""
    to_customer: Decimal
    return_shipping: Decimal
    packaging: Decimal
    total: Decimal


@dataclass
class AmazonFees:
    """Amazon fee breakdown."""
    referral_fee: Decimal
    fulfillment_fee: Decimal
    storage_fee: Decimal
    advertising_fee: Decimal
    total: Decimal


@dataclass
class TaxInfo:
    """Tax information."""
    vat_rate: Decimal
    vat_amount: Decimal
    income_tax_rate: Decimal
    income_tax_amount: Decimal
    total: Decimal


@dataclass
class ProfitCalculationResult:
    """Complete profit calculation result."""
    
    # Input values
    purchase_price: Decimal
    selling_price: Decimal
    marketplace: str
    category: str
    
    # Cost breakdown
    shipping_costs: ShippingCosts
    amazon_fees: AmazonFees
    tax_info: TaxInfo
    
    # Profit calculation
    gross_profit: Decimal
    net_profit: Decimal
    roi_percentage: Decimal
    margin_percentage: Decimal
    
    # Risk assessment
    competition_risk: str
    demand_risk: str
    overall_risk: str
    
    # Metadata
    calculation_date: datetime
    assumptions: Dict[str, Any]


class ProfitCalculator:
    """Calculator for arbitrage profit analysis."""
    
    def __init__(self):
        """Initialize profit calculator with default rates and fees."""
        
        # Amazon referral fee rates by category (%)
        self.referral_fees = {
            CategoryEnum.ELECTRONICS: 8.0,
            CategoryEnum.COMPUTERS: 6.0,
            CategoryEnum.VIDEO_GAMES: 15.0,
            CategoryEnum.BOOKS: 15.0,
            CategoryEnum.CLOTHING: 17.0,
            CategoryEnum.HOME: 15.0,
            CategoryEnum.HEALTH: 8.0,
            CategoryEnum.SPORTS: 15.0,
            CategoryEnum.OTHER: 15.0,
        }
        
        # VAT rates by marketplace (%)
        self.vat_rates = {
            MarketplaceEnum.DE: 19.0,
            MarketplaceEnum.FR: 20.0,
            MarketplaceEnum.ES: 21.0,
            MarketplaceEnum.IT: 22.0,
            MarketplaceEnum.UK: 20.0,
        }
        
        # Base fulfillment fees by marketplace (EUR)
        self.base_fulfillment_fees = {
            MarketplaceEnum.DE: 3.50,
            MarketplaceEnum.FR: 3.50,
            MarketplaceEnum.ES: 3.50,
            MarketplaceEnum.IT: 3.50,
            MarketplaceEnum.UK: 3.20,  # Convert from GBP
        }
        
        # Monthly storage fees per cubic meter (EUR)
        self.storage_fees = {
            MarketplaceEnum.DE: 26.0,
            MarketplaceEnum.FR: 26.0,
            MarketplaceEnum.ES: 26.0,
            MarketplaceEnum.IT: 26.0,
            MarketplaceEnum.UK: 24.0,
        }
        
        # Default assumptions
        self.default_assumptions = {
            "storage_months": 2,  # Average storage time
            "advertising_spend_rate": 0.05,  # 5% of selling price
            "packaging_cost": 2.0,  # EUR per item
            "return_rate": 0.05,  # 5% return rate
            "income_tax_rate": 0.25,  # 25% income tax
            "avg_product_volume": 0.01,  # 1 liter = 0.001 cubic meters
        }
    
    def _calculate_shipping_costs(
        self, 
        purchase_price: Decimal, 
        marketplace: str
    ) -> ShippingCosts:
        """
        Calculate shipping costs.
        
        Args:
            purchase_price: Purchase price from MediaMarkt
            marketplace: Target marketplace
            
        Returns:
            ShippingCosts object
        """
        # Shipping to customer (included in fulfillment fee for FBA)
        to_customer = Decimal("0.00")
        
        # Return shipping (estimated based on return rate)
        return_rate = Decimal(str(self.default_assumptions["return_rate"]))
        avg_return_cost = Decimal("8.00")  # Average return shipping cost
        return_shipping = purchase_price * return_rate * avg_return_cost / purchase_price
        
        # Packaging costs
        packaging = Decimal(str(self.default_assumptions["packaging_cost"]))
        
        total = to_customer + return_shipping + packaging
        
        return ShippingCosts(
            to_customer=to_customer.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            return_shipping=return_shipping.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            packaging=packaging,
            total=total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
    
    def _calculate_amazon_fees(
        self, 
        selling_price: Decimal, 
        marketplace: str, 
        category: str
    ) -> AmazonFees:
        """
        Calculate Amazon fees.
        
        Args:
            selling_price: Selling price on Amazon
            marketplace: Target marketplace
            category: Product category
            
        Returns:
            AmazonFees object
        """
        # Convert strings to enums with fallbacks
        marketplace_enum = MarketplaceEnum(marketplace) if marketplace in [e.value for e in MarketplaceEnum] else MarketplaceEnum.DE
        category_enum = CategoryEnum(category) if category in [e.value for e in CategoryEnum] else CategoryEnum.OTHER
        
        # Referral fee
        referral_rate = Decimal(str(self.referral_fees[category_enum] / 100))
        referral_fee = selling_price * referral_rate
        
        # Fulfillment fee (FBA)
        fulfillment_fee = Decimal(str(self.base_fulfillment_fees[marketplace_enum]))
        
        # Weight-based adjustment (simplified)
        if selling_price > Decimal("100"):  # Assume heavier items for expensive products
            fulfillment_fee *= Decimal("1.5")
        
        # Storage fee (monthly rate * assumed storage time)
        monthly_storage = Decimal(str(self.storage_fees[marketplace_enum]))
        storage_months = Decimal(str(self.default_assumptions["storage_months"]))
        product_volume = Decimal(str(self.default_assumptions["avg_product_volume"]))
        storage_fee = monthly_storage * storage_months * product_volume
        
        # Advertising fee (estimated PPC spend)
        advertising_rate = Decimal(str(self.default_assumptions["advertising_spend_rate"]))
        advertising_fee = selling_price * advertising_rate
        
        total = referral_fee + fulfillment_fee + storage_fee + advertising_fee
        
        return AmazonFees(
            referral_fee=referral_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            fulfillment_fee=fulfillment_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            storage_fee=storage_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            advertising_fee=advertising_fee.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total=total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
    
    def _calculate_taxes(
        self, 
        gross_profit: Decimal, 
        selling_price: Decimal, 
        marketplace: str
    ) -> TaxInfo:
        """
        Calculate tax obligations.
        
        Args:
            gross_profit: Gross profit before taxes
            selling_price: Selling price
            marketplace: Target marketplace
            
        Returns:
            TaxInfo object
        """
        marketplace_enum = MarketplaceEnum(marketplace) if marketplace in [e.value for e in MarketplaceEnum] else MarketplaceEnum.DE
        
        # VAT calculation (on selling price)
        vat_rate = Decimal(str(self.vat_rates[marketplace_enum] / 100))
        vat_amount = selling_price * vat_rate / (Decimal("1") + vat_rate)  # VAT included in price
        
        # Income tax (on profit)
        income_tax_rate = Decimal(str(self.default_assumptions["income_tax_rate"]))
        income_tax_amount = gross_profit * income_tax_rate
        
        total = vat_amount + income_tax_amount
        
        return TaxInfo(
            vat_rate=vat_rate * Decimal("100"),  # Convert back to percentage
            vat_amount=vat_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            income_tax_rate=income_tax_rate * Decimal("100"),
            income_tax_amount=income_tax_amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            total=total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
    
    def _assess_risk(
        self, 
        selling_price: Decimal, 
        category: str, 
        roi_percentage: Decimal
    ) -> Dict[str, str]:
        """
        Assess investment risk factors.
        
        Args:
            selling_price: Selling price
            category: Product category
            roi_percentage: Calculated ROI
            
        Returns:
            Risk assessment dictionary
        """
        # Competition risk based on category
        high_competition_categories = [
            CategoryEnum.ELECTRONICS, 
            CategoryEnum.VIDEO_GAMES,
            CategoryEnum.BOOKS
        ]
        
        category_enum = CategoryEnum(category) if category in [e.value for e in CategoryEnum] else CategoryEnum.OTHER
        
        if category_enum in high_competition_categories:
            competition_risk = "HIGH"
        elif selling_price < Decimal("50"):
            competition_risk = "MEDIUM"
        else:
            competition_risk = "LOW"
        
        # Demand risk based on price point
        if selling_price > Decimal("500"):
            demand_risk = "HIGH"  # Expensive items sell slower
        elif selling_price < Decimal("20"):
            demand_risk = "MEDIUM"  # Low margin items
        else:
            demand_risk = "LOW"
        
        # Overall risk assessment
        risk_factors = [competition_risk, demand_risk]
        if "HIGH" in risk_factors:
            overall_risk = "HIGH"
        elif "MEDIUM" in risk_factors:
            overall_risk = "MEDIUM"
        else:
            overall_risk = "LOW"
        
        # Adjust based on ROI (high ROI might indicate higher risk)
        if roi_percentage > Decimal("100"):  # >100% ROI
            overall_risk = "HIGH"
        
        return {
            "competition_risk": competition_risk,
            "demand_risk": demand_risk,
            "overall_risk": overall_risk
        }
    
    def calculate_profit(
        self, 
        purchase_price: Decimal, 
        selling_price: Decimal,
        marketplace: str = "DE",
        category: str = "Electronics",
        custom_assumptions: Optional[Dict[str, Any]] = None
    ) -> ProfitCalculationResult:
        """
        Calculate complete profit analysis.
        
        Args:
            purchase_price: Purchase price from MediaMarkt
            selling_price: Estimated selling price on Amazon
            marketplace: Target Amazon marketplace
            category: Product category
            custom_assumptions: Custom calculation assumptions
            
        Returns:
            Complete profit calculation result
        """
        try:
            # Merge custom assumptions
            assumptions = self.default_assumptions.copy()
            if custom_assumptions:
                assumptions.update(custom_assumptions)
            
            # Calculate cost components
            shipping_costs = self._calculate_shipping_costs(purchase_price, marketplace)
            amazon_fees = self._calculate_amazon_fees(selling_price, marketplace, category)
            
            # Calculate gross profit
            total_costs = purchase_price + shipping_costs.total + amazon_fees.total
            gross_profit = selling_price - total_costs
            
            # Calculate taxes
            tax_info = self._calculate_taxes(gross_profit, selling_price, marketplace)
            
            # Calculate net profit
            net_profit = gross_profit - tax_info.total
            
            # Calculate performance metrics
            roi_percentage = ((net_profit / purchase_price) * Decimal("100")) if purchase_price > 0 else Decimal("0")
            margin_percentage = ((net_profit / selling_price) * Decimal("100")) if selling_price > 0 else Decimal("0")
            
            # Assess risks
            risk_assessment = self._assess_risk(selling_price, category, roi_percentage)
            
            return ProfitCalculationResult(
                purchase_price=purchase_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                selling_price=selling_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                marketplace=marketplace,
                category=category,
                shipping_costs=shipping_costs,
                amazon_fees=amazon_fees,
                tax_info=tax_info,
                gross_profit=gross_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                net_profit=net_profit.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                roi_percentage=roi_percentage.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
                margin_percentage=margin_percentage.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP),
                competition_risk=risk_assessment["competition_risk"],
                demand_risk=risk_assessment["demand_risk"],
                overall_risk=risk_assessment["overall_risk"],
                calculation_date=datetime.utcnow(),
                assumptions=assumptions
            )
            
        except Exception as e:
            logger.error(f"Error calculating profit: {e}")
            raise
    
    def is_profitable(
        self, 
        result: ProfitCalculationResult, 
        min_roi: Decimal = Decimal("30"),
        min_profit: Decimal = Decimal("10")
    ) -> bool:
        """
        Check if an opportunity meets profitability criteria.
        
        Args:
            result: Profit calculation result
            min_roi: Minimum ROI percentage required
            min_profit: Minimum absolute profit required
            
        Returns:
            True if profitable
        """
        return (
            result.roi_percentage >= min_roi and 
            result.net_profit >= min_profit and
            result.overall_risk != "HIGH"
        )
    
    def format_summary(self, result: ProfitCalculationResult) -> str:
        """
        Format profit calculation summary.
        
        Args:
            result: Profit calculation result
            
        Returns:
            Formatted summary string
        """
        return f"""
Profit Analysis Summary:
------------------------
Purchase Price: €{result.purchase_price}
Selling Price: €{result.selling_price}
Marketplace: {result.marketplace}

Costs:
- Amazon Fees: €{result.amazon_fees.total}
- Shipping: €{result.shipping_costs.total}
- Taxes: €{result.tax_info.total}

Profit:
- Gross Profit: €{result.gross_profit}
- Net Profit: €{result.net_profit}
- ROI: {result.roi_percentage}%
- Margin: {result.margin_percentage}%

Risk Assessment: {result.overall_risk}
        """.strip()


# Convenience functions
def calculate_quick_profit(
    purchase_price: float, 
    selling_price: float,
    marketplace: str = "DE"
) -> ProfitCalculationResult:
    """
    Quick profit calculation with default assumptions.
    
    Args:
        purchase_price: Purchase price from MediaMarkt
        selling_price: Estimated selling price on Amazon
        marketplace: Target marketplace
        
    Returns:
        Profit calculation result
    """
    calculator = ProfitCalculator()
    return calculator.calculate_profit(
        Decimal(str(purchase_price)),
        Decimal(str(selling_price)),
        marketplace
    )


def is_opportunity_profitable(
    purchase_price: float, 
    selling_price: float,
    min_roi: float = 30.0
) -> bool:
    """
    Quick check if an opportunity is profitable.
    
    Args:
        purchase_price: Purchase price
        selling_price: Selling price
        min_roi: Minimum ROI percentage
        
    Returns:
        True if profitable
    """
    result = calculate_quick_profit(purchase_price, selling_price)
    calculator = ProfitCalculator()
    return calculator.is_profitable(result, Decimal(str(min_roi))) 