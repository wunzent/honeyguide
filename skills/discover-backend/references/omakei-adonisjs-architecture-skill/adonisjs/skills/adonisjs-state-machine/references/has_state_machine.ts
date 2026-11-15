// app/lib/has_state_machine.ts
//
// Mixin that adds stateMachine() to Lucid models.
//
// MEMORY SAFETY:
// - State machine class instances are created ONCE per state-machine definition
//   (lazily, on first access) and cached on the *class* (not each model instance).
// - The proxy returned by `model.stateMachine('col')` is a tiny, short-lived
//   wrapper. It does NOT register any listeners or store anything globally.
// - No WeakMap, no Map of model instances, no EventEmitter.

import type { NormalizeConstructor } from '@adonisjs/core/types/helpers'
import type { BaseModel as LucidBaseModel } from '@adonisjs/lucid/orm'
import type { StateMachine } from '#lib/state_machine'

/**
 * A lightweight proxy that binds a StateMachine to a specific model instance
 * for a single call chain. Holds a reference to the model only as long as
 * the variable is in scope — no persistent storage.
 */
class StateMachineProxy<M, S extends string> {
  constructor(
    private machine: StateMachine<any, S>,
    private model: M
  ) {}

  is(state: S): boolean {
    return this.machine.is(this.model, state)
  }

  isAny(states: S[]): boolean {
    return this.machine.isAny(this.model, states)
  }

  currentState(): S {
    return this.machine.currentState(this.model)
  }

  allowedTransitions(): S[] {
    return this.machine.allowedTransitions(this.model)
  }

  canTransitionTo(target: S): boolean {
    return this.machine.canTransitionTo(this.model, target)
  }

  async transitionTo(target: S, metadata?: Record<string, any>): Promise<void> {
    return this.machine.transitionTo(this.model, target, metadata)
  }
}

/**
 * Cache of instantiated state machines, keyed by class constructor + column.
 * Stored on the model *class* (static), not on each instance.
 * One entry per (Model, column) pair — bounded and deterministic.
 */
const machineCache = new Map<string, StateMachine<any, any>>()

/**
 * Mixin to add `stateMachine(column)` to a Lucid model.
 *
 * Usage:
 * ```typescript
 * import { compose } from '@adonisjs/core/helpers'
 * import { HasStateMachine } from '#lib/has_state_machine'
 *
 * class Order extends compose(BaseModel, HasStateMachine) {
 *   static stateMachines = {
 *     status: OrderStateMachine,
 *   }
 * }
 * ```
 */
export function HasStateMachine<T extends NormalizeConstructor<typeof LucidBaseModel>>(
  superclass: T
) {
  class ModelWithStateMachine extends superclass {
    /**
     * Override in each model. Maps column name → StateMachine class.
     * This is a static property — shared across all instances, allocated once.
     */
    static stateMachines: Record<string, new () => StateMachine<any, any>> = {}

    /**
     * Returns a short-lived proxy bound to this model instance.
     *
     * The proxy is created on every call (cheap — plain object, no listeners).
     * It holds a reference to `this` only while the caller holds the proxy.
     * Once the call chain is done and the proxy goes out of scope, both
     * the proxy and its reference to `this` become GC-eligible.
     */
    stateMachine<S extends string>(column: string): StateMachineProxy<this, S> {
      const ctor = (this.constructor as typeof ModelWithStateMachine)
      const MachineClass = ctor.stateMachines[column]

      if (!MachineClass) {
        throw new Error(
          `No state machine registered for column "${column}" on ${ctor.name}`
        )
      }

      // Get or create the singleton machine instance for this (Model, column) pair
      const cacheKey = `${ctor.name}:${column}`
      let machine = machineCache.get(cacheKey)
      if (!machine) {
        machine = new MachineClass()
        machineCache.set(cacheKey, machine)
      }

      return new StateMachineProxy<this, S>(machine, this)
    }
  }

  return ModelWithStateMachine
}
