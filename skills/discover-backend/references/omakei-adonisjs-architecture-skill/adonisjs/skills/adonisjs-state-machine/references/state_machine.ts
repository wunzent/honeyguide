// app/lib/state_machine.ts
//
// Generic, zero-dependency state machine base class for AdonisJS Lucid models.
//
// MEMORY SAFETY:
// - No EventEmitter usage → no listener accumulation
// - `transitions`, `guards`, and `afterTransition` are prototype properties
//   (shared across all instances of a given subclass), NOT per-instance closures
// - The `StateMachineProxy` returned by `stateMachine('col')` is a short-lived
//   object that holds a model reference only for the duration of the call chain.
//   It is GC-eligible immediately after the chain completes.
// - No global WeakMap/Map registry. State is stored in the model's column value.

import db from '@adonisjs/lucid/services/db'

/**
 * Represents a model that has a column with the state value.
 * This keeps the base class framework-agnostic within the type system.
 */
interface StatefulModel {
  [key: string]: any
  save(): Promise<any>
  constructor: { name: string }
}

/**
 * Guard function — throw an Error to block the transition.
 * Receives the model instance for context.
 */
type GuardFn<M> = (model: M) => void | Promise<void>

/**
 * After-transition hook — runs after save.
 * Receives the model instance for side effects (email, event, etc.).
 */
type AfterTransitionFn<M> = (model: M) => void | Promise<void>

/**
 * Base state machine class. Subclass this for each model + state column pair.
 *
 * Generic parameters:
 *   M — the Lucid model type
 *   S — the state enum type (e.g. OrderStatus)
 */
export abstract class StateMachine<M extends StatefulModel, S extends string> {
  /**
   * The model column that stores the state value.
   */
  abstract column: string

  /**
   * Map of allowed transitions: { fromState → allowedToStates[] }
   * Defined on the subclass prototype (shared, not per-instance).
   */
  abstract transitions: Record<S, S[]>

  /**
   * Optional guards keyed by 'from→to'.
   * Each guard should throw an Error to block the transition.
   * Override in subclass. Default: no guards.
   */
  guards: Record<string, GuardFn<M>> = {}

  /**
   * Optional hooks keyed by 'from→to'.
   * Run after the model is saved with the new state.
   * Override in subclass. Default: no hooks.
   */
  afterTransition: Record<string, AfterTransitionFn<M>> = {}

  /**
   * Enable to log every transition to a `state_transitions` table.
   * Override in subclass. Default: false.
   */
  logTransitions: boolean = false

  /**
   * The model type name stored in the audit log.
   * Override in subclass when `logTransitions` is true.
   */
  modelType: string = ''

  // ---------------------------------------------------------------------------
  // Public API — all methods receive the model so the class itself is stateless
  // ---------------------------------------------------------------------------

  /**
   * Get the current state from the model.
   */
  currentState(model: M): S {
    return model[this.column] as S
  }

  /**
   * Check if the model is in a specific state.
   */
  is(model: M, state: S): boolean {
    return this.currentState(model) === state
  }

  /**
   * Check if the model is in any of the provided states.
   */
  isAny(model: M, states: S[]): boolean {
    return states.includes(this.currentState(model))
  }

  /**
   * Get the list of states the model can transition to from its current state.
   */
  allowedTransitions(model: M): S[] {
    return this.transitions[this.currentState(model)] ?? []
  }

  /**
   * Check if transitioning to `target` is structurally allowed
   * (does not run guards).
   */
  canTransitionTo(model: M, target: S): boolean {
    return this.allowedTransitions(model).includes(target)
  }

  /**
   * Perform the transition:
   *  1. Validate the transition is allowed
   *  2. Run the guard (if any) — throws to block
   *  3. Update the column on the model
   *  4. Save the model
   *  5. Log the transition (if enabled)
   *  6. Run the after-transition hook (if any)
   */
  async transitionTo(model: M, target: S, metadata?: Record<string, any>): Promise<void> {
    const from = this.currentState(model)

    // 1. Structural check
    if (!this.canTransitionTo(model, target)) {
      throw new Error(
        `Cannot transition from "${from}" to "${target}" on column "${this.column}"`
      )
    }

    const key = `${from}→${target}`

    // 2. Guard
    const guard = this.guards[key]
    if (guard) {
      await guard(model)
    }

    // 3. Update state
    model[this.column] = target

    // 4. Persist
    await model.save()

    // 5. Audit log
    if (this.logTransitions) {
      await this.recordTransition(model, from, target, metadata)
    }

    // 6. After-transition hook
    const hook = this.afterTransition[key]
    if (hook) {
      await hook(model)
    }
  }

  /**
   * Get all states defined in the transition map.
   */
  allStates(): S[] {
    return Object.keys(this.transitions) as S[]
  }

  /**
   * Get all terminal states (states with no outgoing transitions).
   */
  terminalStates(): S[] {
    return this.allStates().filter((s) => this.transitions[s].length === 0)
  }

  // ---------------------------------------------------------------------------
  // Private
  // ---------------------------------------------------------------------------

  private async recordTransition(
    model: M,
    from: S,
    to: S,
    metadata?: Record<string, any>
  ): Promise<void> {
    await db.table('state_transitions').insert({
      model_type: this.modelType || model.constructor.name,
      model_id: (model as any).id,
      field: this.column,
      from,
      to,
      metadata: metadata ? JSON.stringify(metadata) : null,
      created_at: new Date(),
    })
  }
}
