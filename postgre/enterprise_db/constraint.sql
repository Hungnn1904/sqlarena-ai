-- ============================================
-- ENTERPRISEDB - ADDITIONAL BUSINESS CONSTRAINTS
-- PostgreSQL
-- ============================================

BEGIN;

-- ============================================
-- BR03 - ORDER STATUS
-- ============================================

-- Trạng thái đơn hàng hợp lệ
ALTER TABLE orders
ADD CONSTRAINT chk_orders_status
CHECK (
    status IN (
        'pending',
        'processing',
        'shipped',
        'delivered',
        'cancelled'
    )
);

-- Trạng thái trong lịch sử hợp lệ
ALTER TABLE order_status_history
ADD CONSTRAINT chk_order_history_status
CHECK (
    (old_status IS NULL OR old_status IN (
        'pending',
        'processing',
        'shipped',
        'delivered'
    ))
    AND new_status IN (
        'pending',
        'processing',
        'shipped',
        'delivered',
        'cancelled'
    )
);

-- Chỉ cho phép các chuyển trạng thái hợp lệ
ALTER TABLE order_status_history
ADD CONSTRAINT chk_order_history_transition
CHECK (
       (old_status IS NULL AND new_status = 'pending')
    OR (old_status = 'pending'
        AND new_status IN ('processing', 'cancelled'))
    OR (old_status = 'processing'
        AND new_status IN ('shipped', 'cancelled'))
    OR (old_status = 'shipped'
        AND new_status = 'delivered')
);


-- ============================================
-- BR04 - ORDER TIME
-- ============================================

ALTER TABLE orders
ADD CONSTRAINT chk_orders_timeline
CHECK (
    created_at <= order_date
    AND (shipped_at IS NULL OR shipped_at >= order_date)
    AND (delivered_at IS NULL OR (
        shipped_at IS NOT NULL
        AND delivered_at >= shipped_at
    ))
);


-- ============================================
-- BR05 + BR07 - INVENTORY
-- ============================================

-- Loại giao dịch và số lượng phải phù hợp
ALTER TABLE inventory_transactions
ADD CONSTRAINT chk_inventory_transaction
CHECK (
       (
           transaction_type = 'import'
           AND quantity_change > 0
           AND order_item_id IS NULL
       )
    OR (
           transaction_type = 'sale'
           AND quantity_change < 0
           AND order_item_id IS NOT NULL
       )
    OR (
           transaction_type = 'return'
           AND quantity_change > 0
           AND order_item_id IS NOT NULL
       )
    OR (
           transaction_type = 'adjustment'
           AND quantity_change <> 0
           AND order_item_id IS NULL
       )
);


-- ============================================
-- BR12 - PAYMENTS
-- ============================================

ALTER TABLE payments
ADD CONSTRAINT chk_payment_status
CHECK (
    payment_status IN ('success', 'failed')
);

-- Thay CHECK >= 0 bằng > 0
ALTER TABLE payments
DROP CONSTRAINT chk_payment_amount;

ALTER TABLE payments
ADD CONSTRAINT chk_payment_amount
CHECK (amount > 0);


-- ============================================
-- BR15 - REFUND TIME
-- ============================================

ALTER TABLE refunds
ADD CONSTRAINT chk_refund_timeline
CHECK (
    completed_at IS NULL
    OR completed_at >= requested_at
);

COMMIT;


-- ============================================
-- PARTIAL UNIQUE INDEXES
-- ============================================

-- BR07: Mỗi order_item chỉ xuất kho tối đa 1 lần
CREATE UNIQUE INDEX uq_inventory_sale_order_item
ON inventory_transactions(order_item_id)
WHERE transaction_type = 'sale';

-- BR07: Mỗi order_item chỉ trả kho tối đa 1 lần
CREATE UNIQUE INDEX uq_inventory_return_order_item
ON inventory_transactions(order_item_id)
WHERE transaction_type = 'return';

-- BR12: Mỗi đơn chỉ có tối đa 1 payment thành công
CREATE UNIQUE INDEX uq_payment_success_per_order
ON payments(order_id)
WHERE payment_status = 'success';