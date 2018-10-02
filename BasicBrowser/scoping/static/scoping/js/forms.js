$('.other').on('click', function () {
    console.log($(this))
    r = $(this).parent()
    name = r.data()['name']
    inputs = r.children('input,select')
    //inputs.each(function(i,v){
    $.each(inputs, function(i,v) {
        console.log(v)
        v.classList.toggle('hidden');
        if (v.name==name) {
            v.removeAttribute('name')
        } else {
            v.name=name
        }
    })
    t = ($(this))
    if ($(this).text()=="Other") {
        $(this).text("Choices")
    } else {
        $(this).text("Other")
    }
 });
