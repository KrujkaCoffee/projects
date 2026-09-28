<?
require($_SERVER["DOCUMENT_ROOT"] . "/bitrix/header.php");
$APPLICATION->SetPageProperty("keywords", "Kontakte Powerz");
$APPLICATION->SetPageProperty("description", "Kontakte Powerz");
$APPLICATION->SetPageProperty("title", "Kontakte Powerz");
$APPLICATION->SetTitle("Kontakte");
?><div class="row com_contacts_info">
	<h2>Powerz GmbH</h2>
	<div class="row">
		<div class="item address">
 <span class="img_wrap"><img src="/bitrix/themes/powerz_new-v2/images/tpl/ico_address2.png"></span>
			<p>
				 Neuhofen 3, 94167 Tettenweis, Germany
			</p>
		</div>
		<div class="item phone">
 <span class="img_wrap"><img src="/bitrix/themes/powerz_new-v2/images/tpl/ico_phone2.png"></span>
			<p>
				 +49 (0) 8534 969 34 79
			</p>
		</div>
		<div class="item email">
 <span class="img_wrap"><img src="/bitrix/themes/powerz_new-v2/images/tpl/ico_email.png"></span>
			<p>
 <a href="mailto:info@powerz.co">info@powerz.co</a>
			</p>
		</div>
	</div>
	 <!--<div class="sheme">
                    <img id="bxid_474680" src="/bitrix/images/fileman/htmledit2/script.gif"  />
                </div>-->
</div>
<div class="row com_contacts_form">
	<h4>KONTAKTIEREN SIE UNS </h4>
	 <?$APPLICATION->IncludeComponent(
	"3xweb:main.feedback",
	"",
	Array(
		"EMAIL_TO" => "info@powerz.co",
		"EVENT_MESSAGE_ID" => array(),
		"EVENT_NAME" => "feedback_de",
		"OK_TEXT" => "Danke, Ihre Nachricht wird akzeptiert.",
		"REQUIRED_FIELDS" => array("NAME","EMAIL","PHONE","MESSAGE"),
		"USE_CAPTCHA" => "Y"
	)
);?>
</div>
<script>
	$(document).ready(function(){
        $('#feedbackSubmit').click(function(){
            if($('#upload_check_0').is(':checked')){
            }else{
                alert('Geben Sie Ihre Zustimmung zur Datenverarbeitung!');
                return false;
            }
        });
    });
</script><?

require($_SERVER["DOCUMENT_ROOT"] . "/bitrix/footer.php"); ?>