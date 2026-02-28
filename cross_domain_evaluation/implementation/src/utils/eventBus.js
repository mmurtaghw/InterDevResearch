
/**
 * @file eventBus.js
 * @description This file sets up and exports an event bus using the mitt library.
 * @module utils/eventBus
 */

 /**
    * @typedef {import('mitt').Emitter} Emitter
    */

 /**
    * @type {Emitter}
    * @description An instance of mitt used as an event bus for emitting and listening to events.
    */
import mitt from 'mitt';

const eventBus = mitt();

export default eventBus;
