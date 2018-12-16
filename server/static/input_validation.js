function sanitize(var s){
  var replacement = s.replace(/[&]/g, "&amp");
  replacement = replacement.replace(/[<]/g, "&lt");
  replacement = replacement.replace(/[>]/g, "&gt");
  replacement = replacement.replace(/["]/g, "&quot");
  replacement = replacement.replace(/[']/g, "&#x27");
  replacement = replacement.replace(/[/]/g, "&#x2F");
  return replacement
}

function email_validity(var s){
  if (/^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$/.test(myForm.emailAddr.value))
  {
    return true
  }
  alert("You have entered an invalid email address!")
  return false
}


function password_equal(){
  var password = document.getElementById("reg_password")
  var confirm_password = document.getElementById("reg_confirm_password")
  if(password != confirm_password){
    alert('The values in password and confirm password fields do not match. Please verify and try again')
    return false
  }
  return true
}

function input_sanitization() {
  var password = document.getElementById("reg_password")
  if password != null) {
	if (! /^[a-zA-Z0-9@._!()-+*^]+$/.test(password)){
	  alert('Invalid Password. Please conform to password policy')
	  document.getElementById("reg_password").value = "";
	  if password_equal() {
	    document.getElementById("reg_confirm_password").value = "";
	  }
	  return false
    }
  }
  
  var arr = document.getElementsByClassName('validate_input')
  var replacement = null
  if arr.length > 0 {
    for (var x = 0; x < arr.length; x++) {
      replacement = sanitize(arr[x])
      document.getElementsByClassName('validate_input')[x].value = replacement
    }
  }
  
  var arr1 = document.getElementsByClassName('validate_email')
  if arr1.length > 0{
    for (var x = 0; x < arr.length; x++) {
      if email_validity(arr1[x]) == false { 
		alert('Invalid Email Address') 
		return false 
      }
    }
  }
  return true
}

