"use strict";

import {
    trigger
} from "./utils"
import timeline from "./timeline";
import $ from "jquery"
import ClipboardActionCopy from 'clipboard/src/actions/copy'
import 'jquery-ui-pack'

// Foundation
import {
    Foundation
} from './foundation-sites/js/foundation.core';
import * as CoreUtils from './foundation-sites/js/foundation.core.utils';
import {
    Motion,
    Move
} from './foundation-sites/js/foundation.util.motion';
import {
    Touch
} from './foundation-sites/js/foundation.util.touch';
import {
    Toggler
} from './foundation-sites/js/foundation.toggler';
import {
    Tooltip
} from './foundation-sites/js/foundation.tooltip';
import {
    Box
} from './foundation-sites/js/foundation.util.box';
import {
    MediaQuery
} from './foundation-sites/js/foundation.util.mediaQuery';
import { 
    Triggers 
} from './foundation-sites/js/foundation.util.triggers';


let timelineCrawlForwardInterval = null
let timelineCrawlForwardTimeout = null
let timelineCrawlBackwardInterval = null
let timelineCrawlBackwardTimeout = null
var timelineInstance = null

//$.fn.extend({
//    trigger: function triggerHack(eventType, extraParameters) {
//        trigger(eventType, extraParameters, this.get(0), true)
//    },
//})

//const toggleListener = context => {
//    function toggleListenerImpl() {
//        let ids = $(this).data('toggle')
//        console.log(ids)
//        if (ids) {
//            ids.split(" ").forEach(id => {
//                const element = $(`#${id}`, context)
//                console.log(element, context)
//                trigger("toggle.zf.trigger", [$(this)], element.get(0), true)
//            })
//        } else {
//            trigger("toggle.zf.trigger", {}, this, true)
//        }
//    }
//    return toggleListenerImpl
//}
// const addToggleListener = context => {
//     context.off("click.zf.trigger", toggleListener(context))
//     context.on("click.zf.trigger", '[data-toggle]', toggleListener(context))
// }

function* querySelectorAll({node, selector}) {
    // This generator is like querySelectorAll except that it can also match the current node.
    // It is tempting to stick this into Document and HTMLElement prototypes under some weird name.
    if ('matches' in node && node.matches(selector)) {
        yield node
    }
    for (const match of node.querySelectorAll(selector)) {
        yield match
    }
}

class KronofotoContext {
    constructor({htmx, context}) {
        this.htmx = htmx
        this.context = context
    }
    addZoom(container) {
        let imgsrc = container.currentStyle || window.getComputedStyle(container, false);
        imgsrc = imgsrc.backgroundImage.slice(4, -1).replace(/"/g, "");

        let img = new Image();
        let zoomOpened = false
        let zoomed = false
        let galleryElem = this.context.querySelector('.gallery')[0]
        img.src = imgsrc;
        img.onload = () => {


            let ratio = img.naturalWidth / img.naturalHeight;

            Object.assign(container.style, {
                height: "calc(100vh)",
                width: "calc(100vw)",
                backgroundPosition: "top",
                backgroundSize: "contain",
                backgroundRepeat: "no-repeat"
            });

            let removeZoom = () => {
                Object.assign(container.style, {
                    backgroundPosition: "top",
                    backgroundSize: "contain"
                });
            }

            container.addEventListener('click', (e) => {
                zoomed = !zoomed;

                if (zoomed) {
                    galleryElem.classList.add('zoomed')
                } else {
                    galleryElem.classList.remove('zoomed')
                    removeZoom()
                }
            })

            container.onmousemove = (e) => {
                if (zoomed) {
                    let rect = e.target.getBoundingClientRect(),
                        xPos = e.clientX - rect.left,
                        yPos = e.clientY - rect.top,
                        xPercent = ((xPos / container.clientWidth) * 100) + "%",
                        yPercent = ((yPos / container.clientHeight) * 100) + "%";

                    Object.assign(container.style, {
                        backgroundPosition: xPercent + " " + yPercent,
                        backgroundSize: (window.innerWidth * 1.5) + "px"
                    });
                }
            };

            // container.onmouseleave = removeZoom

        }
    }
    onLoad(elem) {
        $("[data-autocomplete-url]", elem).each((_, input) => {
            const $input = $(input)
            $input.autocomplete({
                source: $input.data("autocomplete-url"),
                minLength: $input.data("autocomplete-min-length"),
            })
        })
        $(elem).find(".form--add-tag .link--icon").on('click', (e) => {
            let $form = $(e.currentTarget).closest('form')
            $form.addClass('expanded')
            $('input[type=text]', $form).get(0).focus()
        })
        // this logic should not be client side
        $(elem).find('[data-save-list]').on('submit', e => {
            // Check if logged in
            if ($('#login-btn', this.context).length) {
                $('#login-btn', this.context).trigger('click')
                showToast('You must login to continue')
            } else {
                showToast('Updated photo lists')
            }
        })
        // the next three have some broken state.
        $('#overlay', elem).on('click', (e) => {
            this.htmx.trigger("#hamburger-button", "click")
            $('#overlay', this.context).fadeOut()
        })
        $('#hamburger-menu', elem).on('off.zf.toggler', (e) => {
            $('#login', this.context).addClass('collapse')
            $('#overlay', this.context).fadeIn()
        }).on('on.zf.toggler', (e) => {
            if ($('#login', this.context).hasClass('collapse')) {
                $('#overlay', this.context).fadeOut()
            }
        })
        $('#login', elem).on('off.zf.toggler', (e) => {
            $('#hamburger-menu', this.context).addClass('collapse')
            $('#overlay', this.context).fadeIn()
        }).on('on.zf.toggler', (e) => {
            if ($('#hamburger-menu', this.context).hasClass('collapse')) {
                $('#overlay', this.context).fadeOut()
            }
        })
        $('#auto-play-image-control-button', elem).on('click', (e) => {
            let $btn = e.currentTarget
            $btn.classList.toggle('active')
            if ($btn.classList.contains('active')) {
                this.autoplayStart($btn)
            } else {
                this.autoplayStop()
            }
        })
        $(elem).find(".image-control-button--toggle").on('click', (e) => {
            let $btn = $(e.currentTarget)
            $('img', $btn).toggleClass('hide')
        })
        for (const elem2 of elem.querySelectorAll("#follow-zoom-timeline-version")) {
            this.addZoom(elem2)
        }

        for (const elem2 of querySelectorAll({node: elem, selector: "#backward-zip"})) {
            elem2.addEventListener("click", this.timelineZipBackward.bind(this))
            elem2.addEventListener("mousedown", this.timelineCrawlBackward.bind(this))
            elem2.addEventListener("mouseup", this.timelineCrawlBackwardRelease.bind(this))
        }
        for (const elem2 of querySelectorAll({node: elem, selector: "#forward-zip"})) {
            elem2.addEventListener("click", this.timelineZipForward.bind(this))
            elem2.addEventListener("mousedown", this.timelineCrawlForward.bind(this))
            elem2.addEventListener("mouseup", this.timelineCrawlForwardRelease.bind(this))
        }
        if (elem.querySelectorAll(".photos-timeline").length) {
            timelineInstance = undefined
            this.initTimeline()
        }
        this.initDraggableThumbnails(elem)
        initNavSearch(elem)
        // modified this foundation function to attach a "rootNode" variable to all plugin objects.
        // The foundation function already accepts one optional argument, so undefined is passed to preserve
        // the old behavior.
        $(elem).foundation(undefined, this.context)
        if (window.st && elem.querySelectorAll('.sharethis-inline-share-buttons').length) {
            st.initialize()
        }
        this.initGalleryNav(elem)

        // Init gallery thumbnails
        if (elem.id == 'fi-preload-zone') {
            this.slideToId({
                fi: elem.getAttribute("data-slide-id"),
                target: "[data-fi-thumbnail-carousel-images]",
            })
            setTimeout(() => {
                let html = elem.innerHTML
                // let firstId = $(html).find('li:first-child span').attr('hx-get')
                const carouselImages = elem.parentNode.querySelector('#fi-thumbnail-carousel-images')
                carouselImages.innerHTML = html
                carouselImages.classList.add("dragging")
                carouselImages.style.left = "0px"
                setTimeout(() => {
                    carouselImages.classList.remove('dragging')
                }, 100)

                this.htmx.process(carouselImages)
                elem.replaceChildren()
            }, 250)
        }
        $("#fi-image", elem).on("click", () => console.log("clicked"))

        /*  disabled until different solution is tried (set attributes without replacing tag)

            if ($('#fi-image-preload img').length && !$('#fi-image-preload img').data('loaded')) {
              $('#fi-image-preload img').data('loaded', true)
              let url = $('#fi-image-preload img').attr('src')
              const image = new Image();
              image.src = url;
              image.onload = () => {
                let html = $('#fi-image-preload').html()
                $('#fi-image').html(html)
                $('#fi-image-preload').empty()
              }
            }
        */
    }
    initDraggableThumbnails(newElems) {
        let elem = undefined
        let released = false
        const handler = evt => {
            if (!released || !evt.detail.elt.parentElement.attributes.getNamedItem("data-active")) {
                console.log("preventing", evt)
                evt.preventDefault()
            } else {
                console.log("allowing", evt)
                setTimeout(() => elem.removeEventListener("htmx:confirm", handler), 100)
            }
        }
        $('#fi-thumbnail-carousel-images', newElems).draggable({
            axis: 'x',
            drag: (event, ui) => {
                if (!elem) {
                    elem = event.target
                    console.log("installing htmx:confirm handler", elem)
                    elem.addEventListener("htmx:confirm", handler)
                }
                this.moveTimelineCoin(ui.position.left, true)
            },
            stop: (event, ui) => {
                this.dropTimelineCoin(ui.position.left)
                released = true
                for (const temp of this.context.querySelectorAll('#fi-thumbnail-carousel-images li[data-active] a')) {
                    trigger("click", {}, temp, true)
                }
            }
        })
    }
    initTimeline() {
        if (!timelineInstance) {
            timelineInstance = new timeline();
            $('.photos-timeline', this.context).each((i, e) => {
                timelineInstance.connect(e, this.context);
            })
        }
        return timelineInstance
    }
    getNumVisibleTimelineTiles() {
        let widthOfTimeline = $('#fi-image', this.context).width() // assumes the timeline is the same width as gallery image
        let $li = $('#fi-thumbnail-carousel-images li[data-active]', this.context)
        let widthOfTile = $li.outerWidth()
        return Math.floor(widthOfTimeline / widthOfTile)
    }
    timelineZipForward() {
        if (timelineCrawlForwardInterval == null) { // only zip if we're not already crawling
            let numToZip = Math.floor((this.getNumVisibleTimelineTiles() - 0.5))
            let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]', this.context)
            let $nextLi = $activeLi.nextAll().eq(numToZip)
            //gotoTimelinePosition(numToZip)
            trigger("click", {}, $nextLi.find('a').get(0), true)
        }
        return false
    }
    timelineZipBackward() {
        if (timelineCrawlBackwardInterval == null) { // only zip if we're not already crawling
            let numToZip = Math.floor((this.getNumVisibleTimelineTiles() - 0.5))
            let $activeLi = $('#fi-thumbnail-carousel-images li[data-active]', this.context)
            let $nextLi = $activeLi.prevAll().eq(numToZip)
            trigger("click", {}, $nextLi.find('a').get(0), true)
        }
        return false
    }
    timelineCrawlForward() {
        timelineCrawlForwardTimeout = setTimeout(() => {
            let currentPosition = $('#fi-thumbnail-carousel-images', this.context).position().left
            timelineCrawlForwardInterval = setInterval(() => {
                if (this.canCrawlForward()) {
                    currentPosition -= 20
                    $('#fi-thumbnail-carousel-images', this.context).css('left', currentPosition)
                    this.moveTimelineCoin(currentPosition, true)
                }
            }, 50)
        }, 500)
    }
    timelineCrawlBackward() {
        timelineCrawlBackwardTimeout = setTimeout(() => {
            let currentPosition = $('#fi-thumbnail-carousel-images', this.context).position().left
            timelineCrawlBackwardInterval = setInterval(() => {
                if (this.canCrawlBackward()) {
                    currentPosition += 20
                    $('#fi-thumbnail-carousel-images', this.context).css('left', currentPosition)
                    this.moveTimelineCoin(currentPosition, true)
                }
            }, 50)
        }, 500)
    }
    timelineCrawlForwardRelease() {
        clearTimeout(timelineCrawlForwardTimeout)
        timelineCrawlForwardTimeout = null
        if (timelineCrawlForwardInterval) { // only execute when we're crawling
            clearInterval(timelineCrawlForwardInterval)
            this.dropTimelineCoin($('#fi-thumbnail-carousel-images', this.context).position().left)
            trigger("click", {}, $('#fi-thumbnail-carousel-images li[data-active] a', this.context).get(0), true)
            setTimeout(() => {
                timelineCrawlForwardInterval = null
            }, 750)
        }
    }

    timelineCrawlBackwardRelease() {
        clearTimeout(timelineCrawlBackwardTimeout)
        timelineCrawlBackwardTimeout = null
        if (timelineCrawlBackwardInterval) { // only execute when we're crawling
            clearInterval(timelineCrawlBackwardInterval)
            this.dropTimelineCoin($('#fi-thumbnail-carousel-images', this.context).position().left)
            trigger("click", {}, $('#fi-thumbnail-carousel-images li[data-active] a', this.context).get(0), true)
            setTimeout(() => {
                timelineCrawlBackwardInterval = null
            }, 750)
        }
    }
    canCrawlBackward() {
        let length = $('#fi-thumbnail-carousel-images [data-active]', this.context).prevAll().length
        return length > 10
    }
    canCrawlForward() {
        let length = $('#fi-thumbnail-carousel-images [data-active]', this.context).nextAll().length
        return length > 10
    }
    autoplayStart(elem) {
        // should change `window` to `this`
        window.autoplayTimer = setInterval(elem => {
            if (elem.isConnected) {
                this.htmx.trigger('#fi-arrow-right', 'click')
            } else {
                clearInterval(window.autoplayTimer)
            }
        }, 5000, elem)
    }
    autoplayStop() {
        clearInterval(window.autoplayTimer)
    }
    slideToId({target, fi}) {
        for (const targets of this.context.querySelectorAll(target)) {
            let destination, candidate = undefined
            for (const elem of targets.querySelectorAll(`:scope > [data-fi="${fi}"]`)) {
                candidate = elem
                for (const img of elem.querySelectorAll(":scope a img")) {
                    if (!img.classList.contains("empty")) {
                        destination = candidate
                    }
                }
            }
            if (!destination) {
                destination = candidate
            }
            const origin = targets.querySelector(`:scope [data-origin]`)
            if (destination && origin) {
                const children = [...targets.children]
                const delta = children.indexOf(destination) - children.indexOf(origin)
                this.gotoTimelinePosition(delta)
            }
        }
    }
    gotoTimelinePosition(delta) {
        let width = $('#fi-thumbnail-carousel-images li', this.context).outerWidth()
        this.moveTimelineCoin(delta * -1 * width, false)
        this.dropTimelineCoin(delta * -1 * width)
    }
    moveTimelineCoin(deltaX, drag = true) {
        if (drag) {
            $('#fi-thumbnail-carousel-images', this.context).addClass('dragging')
        } else {
            $('#fi-thumbnail-carousel-images', this.context).removeClass('dragging')
        }
        let widthOfThumbnail = $('#fi-thumbnail-carousel-images li', this.context).outerWidth()
        let preItemNum = $('#fi-thumbnail-carousel-images [data-origin]', this.context).index()
        let quantizedPositionX = (Math.round(deltaX / widthOfThumbnail) * -1)
        let currentPosition = preItemNum + quantizedPositionX + 1

        let numThumbnails = $('#fi-thumbnail-carousel-images li', this.context).length
        //console.log({numThumbnails, currentPosition, preItemNum})

        if (drag && numThumbnails - currentPosition < 20) {
            const form = $('#fi-thumbnail-carousel-images', this.context).closest("form").get(0)
            form.querySelector("[name='forward']").value = 1
            form.setAttribute("hx-swap", "beforeend")

            const child = form.querySelector("#fi-thumbnail-carousel-images li:last-child")
            const lastFI = child.getAttribute("data-fi")
            const offset = $(child).position().left
            const width = $(child).outerWidth()

            form.querySelector("[name='offset']").value = offset
            form.querySelector("[name='width']").value = width

            form.querySelector("[name='id']").value = lastFI
            trigger("kronofoto:loadThumbnails", {}, $("#fi-thumbnail-carousel-images", this.context).get(0), true)
        } else if (drag && currentPosition < 20) {
            /* copy/pasted code */
            const form = $('#fi-thumbnail-carousel-images', this.context).closest("form").get(0)
            form.setAttribute("hx-swap", "afterbegin")
            form.querySelector("[name='forward']").value = ""
            const child = form.querySelector("#fi-thumbnail-carousel-images li:first-child")
            const lastFI = child.getAttribute("data-fi")
            const offset = $(child).position().left
            const width = $(child).outerWidth()

            form.querySelector("[name='offset']").value = offset
            form.querySelector("[name='width']").value = width
            form.querySelector("[name='id']").value = lastFI
            trigger("kronofoto:loadThumbnails", {}, $("#fi-thumbnail-carousel-images", this.context).get(0), true)
        }

        $('#fi-thumbnail-carousel-images li', this.context).removeAttr('data-active')
        $('#fi-thumbnail-carousel-images li:nth-child(' + currentPosition + ')', this.context).attr('data-active', '')
    }
    dropTimelineCoin(deltaX) {
        let width = $('#fi-thumbnail-carousel-images li', this.context).outerWidth()
        let quantizedX = (Math.round(deltaX / width))
        let itemNum = quantizedX
        $('#fi-thumbnail-carousel-images', this.context).css({
            left: itemNum * width
        })
    }
    initGalleryNav(elem) {
        // When the mouse moves
        for (const gallery of querySelectorAll({node: elem, selector: ".control"})) {
            let hideGalleryTimeout = null;
            gallery.addEventListener('mousemove', () => {
                this.showGalleryNav()
                if (hideGalleryTimeout)
                    clearTimeout(hideGalleryTimeout)
                hideGalleryTimeout = setTimeout(this.hideGalleryNav.bind(this), 5000)
            })
        }
    }
    showGalleryNav() {
        $(".gallery", this.context).removeClass('hide-nav')
    }
    hideGalleryNav() {
        $(".gallery", this.context).addClass('hide-nav')
    }
}

export const initHTMXListeners = (_htmx, context, {
    lateLoad = false
} = {}) => {

    // context here means our root element
    // necessary?
    $(context).on('click', (e) => {
        if (!$('.form--add-tag input', context).is(":focus")) {
            let $form = $('.form--add-tag input', context).closest('form')
            $form.removeClass('expanded')
        }
    })

    // context here means our root element and this would probably be simpler with server side templates.
    $(context).on('on.zf.toggler', function(e) {
        if ($(e.target).hasClass('gallery__popup')) {
            $('.gallery__popup.expanded:not(#' + $(e.target).attr('id') + ')').removeClass('expanded')
        }
    })

    const instance = new KronofotoContext({htmx: _htmx, context})
    if (lateLoad) {
        instance.onLoad(context)
    }
    _htmx.onLoad(instance.onLoad.bind(instance))
}
export function initFoundation(context) {

    Foundation.addToJquery($);
    Foundation.Box = Box;
    Foundation.MediaQuery = MediaQuery;
    Foundation.Motion = Motion;
    Foundation.Move = Move;

    Triggers.Initializers.addToggleListener($(context))
    Foundation.plugin(Toggler, 'Toggler');
    Foundation.plugin(Tooltip, 'Tooltip');
}

export function initClipboardJS(context) {
    $(context).on('click', '.copy-button', (e) => {
        let target = $(e.currentTarget).attr('data-clipboard-target')
        let text = $(target).val()
        ClipboardActionCopy(text)
        $(target).select()
        $(target)[0].setSelectionRange(0, 999999)
    })
}
export function collapseNavSearch(elem) {
    return () => {
        $('#search-box-container', elem).removeClass('expanded')
        $('.search-form', elem).hide()
        $('#search-box', elem).val('')
        $('.search-icon', elem).css('filter', 'none')
        $('.carrot', elem).css('filter', 'none')
        $('#search-box', elem).removeClass('placeholder-light').css('color', '#333')
    }
}

export function expandNavSearch(elem) {
    return () => {
        $('#search-box-container', elem).addClass('expanded')
        $('.search-form', elem).show()
        $('.search-icon', elem).css('filter', 'brightness(0) invert(1)')
        $('.carrot', elem).css('filter', 'brightness(0) invert(1)')
        $('#search-box', elem).addClass('placeholder-light').css('color', 'white')
    }
}
export function initNavSearch(elem) {
    $('.search-form__clear-btn', elem).click((e) => {
        e.preventDefault();
        $('#search-box', elem).val('')
        $('.search-form input[type=text]', elem).val('')
        $('.search-form select', elem).val('')
    })
    $('#search-box', elem).click(expandNavSearch(elem))
    $('#search-box-container .close-icon', elem).click(collapseNavSearch(elem))
}

export function showToast(message) {
    let content = $('#toast-template').html()
    let $message = $(content)
    $message.prepend('<p>' + message + '</p>')
    $('#messages').append($message)
    setTimeout(() => {
        $message.fadeOut(() => {
            $message.remove()
        })
    }, 5000)
}

let moreThumbnailsLoading = false


export function toggleLogin(evt) {
    const el = document.querySelector('#login');
    toggleElement(el);
}
export function toggleMenu(evt) {
    // if(!$('.hamburger').hasClass('is-active')) {
    //   $('.hamburger').addClass('is-active')
    //   $('.hamburger-menu').removeClass('collapse')
    //   $('body').addClass('menu-expanded')
    //   $('.overlay').fadeIn()
    // }
    // else {
    //   $('.hamburger').removeClass('is-active')
    //   $('.hamburger-menu').addClass('collapse')
    //   $('body').removeClass('menu-expanded')
    //   $('.overlay').fadeOut()
    // }
}

function toggleElement(el) {
    if (!el.classList.replace('hidden', 'gridden')) {
        el.classList.replace('gridden', 'hidden')
    }
}

export const installButtons = root => content => {
    const elems = Array.from(content.querySelectorAll('[data-popup-target]'))

    if (content.hasAttribute('data-popup-target')) {
        elems.push(content)
    }

    for (const elem of elems) {
        const datatarget = elem.getAttribute('data-popup-target')
        elem.addEventListener("click", evt => {
            for (const target of root.querySelectorAll('[data-popup]')) {
                if (target.hasAttribute(datatarget)) {
                    target.classList.remove("hidden")
                } else {
                    target.classList.add('hidden')
                }
            }
            elem.dispatchEvent(new Event(datatarget, {
                bubbles: true
            }))
        })
    }
}
