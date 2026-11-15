// app/state_machines/order_state_machine.ts
//
// Example state machine for an Order model.
// Demonstrates transitions, guards, and after-transition hooks.

import { StateMachine } from '#lib/state_machine'
import { OrderStatus } from '#enums/order_status'
import type Order from '#models/order'

export class OrderStateMachine extends StateMachine<Order, OrderStatus> {
  column = 'status' as const

  // ── Transition map ───────────────────────────────────────────
  // Static declaration — allocated once on the class prototype.
  // No closures, no per-instance allocation, no memory leak.

  transitions = {
    [OrderStatus.Draft]: [OrderStatus.Pending, OrderStatus.Cancelled],
    [OrderStatus.Pending]: [OrderStatus.Paid, OrderStatus.Cancelled],
    [OrderStatus.Paid]: [OrderStatus.Shipped, OrderStatus.Cancelled],
    [OrderStatus.Shipped]: [OrderStatus.Completed],
    [OrderStatus.Completed]: [],    // terminal
    [OrderStatus.Cancelled]: [],    // terminal
  }

  // ── Guards ───────────────────────────────────────────────────
  // Each guard receives the model and should throw if the transition
  // is not allowed. Guards are plain functions (no closure capture).

  guards = {
    'draft→pending': async (order: Order) => {
      if (order.totalInCents <= 0) {
        throw new Error('Order total must be greater than zero to submit')
      }
    },
    'pending→paid': async (order: Order) => {
      if (!order.paymentId) {
        throw new Error('Cannot mark as paid without a payment ID')
      }
    },
    'paid→shipped': async (order: Order) => {
      if (!order.shippingAddress) {
        throw new Error('Shipping address is required before shipping')
      }
    },
  }

  // ── After-transition hooks ───────────────────────────────────
  // Run after the model has been saved with the new state.
  // Use for side effects: emails, events, external API calls.
  //
  // IMPORTANT: Do NOT store references to the model outside
  // of these functions. They receive the model as a parameter
  // and should not capture it in any outer scope.

  afterTransition = {
    'draft→pending': async (_order: Order) => {
      // Example: notify admin of new order submission
      // await emitter.emit('order:submitted', { orderId: order.id })
    },
    'pending→paid': async (_order: Order) => {
      // Example: send payment confirmation email
      // await mail.send(new OrderPaidEmail(order))
    },
    'paid→shipped': async (_order: Order) => {
      // Example: notify warehouse, generate tracking number
      // await warehouseService.createShipment(order)
    },
    'shipped→completed': async (_order: Order) => {
      // Example: send delivery confirmation
      // await mail.send(new OrderDeliveredEmail(order))
    },
    'pending→cancelled': async (_order: Order) => {
      // Example: release reserved inventory
      // await inventoryService.release(order)
    },
    'paid→cancelled': async (_order: Order) => {
      // Example: initiate refund
      // await paymentService.refund(order.paymentId)
    },
  }

  // Enable audit trail (requires state_transitions table)
  logTransitions = false
  modelType = 'Order'
}

// ---------------------------------------------------------------------------
// Supporting enum (also lives in app/enums/order_status.ts)
// ---------------------------------------------------------------------------

// export enum OrderStatus {
//   Draft = 'draft',
//   Pending = 'pending',
//   Paid = 'paid',
//   Shipped = 'shipped',
//   Completed = 'completed',
//   Cancelled = 'cancelled',
// }

// ---------------------------------------------------------------------------
// Model integration (also lives in app/models/order.ts)
// ---------------------------------------------------------------------------

// import { BaseModel, column } from '@adonisjs/lucid/orm'
// import { compose } from '@adonisjs/core/helpers'
// import { HasStateMachine } from '#lib/has_state_machine'
// import { OrderStateMachine } from '#state_machines/order_state_machine'
// import { OrderStatus } from '#enums/order_status'
//
// export default class Order extends compose(BaseModel, HasStateMachine) {
//   static stateMachines = {
//     status: OrderStateMachine,
//   }
//
//   @column({ isPrimary: true })
//   declare id: number
//
//   @column()
//   declare status: OrderStatus
//
//   @column()
//   declare totalInCents: number
//
//   @column()
//   declare paymentId: string | null
//
//   @column()
//   declare shippingAddress: string | null
//
//   // ── Convenience methods ─────────────────────────
//
//   get isEditable() {
//     return this.status === OrderStatus.Draft
//   }
//
//   get isCancellable() {
//     return this.stateMachine('status').canTransitionTo(OrderStatus.Cancelled)
//   }
//
//   async submit() {
//     await this.stateMachine('status').transitionTo(OrderStatus.Pending)
//   }
//
//   async markPaid(paymentId: string) {
//     this.paymentId = paymentId
//     await this.save()
//     await this.stateMachine('status').transitionTo(OrderStatus.Paid)
//   }
//
//   async ship() {
//     await this.stateMachine('status').transitionTo(OrderStatus.Shipped)
//   }
//
//   async complete() {
//     await this.stateMachine('status').transitionTo(OrderStatus.Completed)
//   }
//
//   async cancel() {
//     await this.stateMachine('status').transitionTo(OrderStatus.Cancelled)
//   }
// }
